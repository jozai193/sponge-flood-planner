"""Assess frozen historical runs against every compatible in-domain STN mark."""
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from pyproj import Transformer

from services.reference.observations import compare_peak_elevations
from services.reference.replay_integrity import validate_replay
from services.reference.site_metrics import site_balanced_errors

root=Path(sys.argv[1])
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protocol=json.loads((root/'protocol.json').read_text())
protocol_hash=(root/'protocol.sha256').read_text().strip()
if digest(root/'protocol.json')!=protocol_hash:raise ValueError('Protocol changed')
for path,expected in protocol['source_sha256'].items():
    if digest(Path(path))!=expected:raise ValueError('Frozen source changed: '+path)
marks=json.loads((root/'hwms.json').read_text())
review=json.loads((root/protocol['observation_review']).read_text())['marks'] if protocol.get('observation_review') else None
quality={r['hwm_quality_id']:r['hwm_quality'] for r in json.loads(Path('artifacts/validation/sandy-2012/quality-lookup.json').read_text())}
crs_by_id={2:'EPSG:4269',3:'EPSG:4267',4:'EPSG:4326'}
runs=[]
for run in protocol['bundles']:
    n=run['grid_cells'];path=root/f'simulation-{n}.json'
    sim=json.loads(path.read_text())
    if sim.get('protocol_sha256')!=protocol_hash:raise ValueError('Simulation does not match frozen protocol')
    if sim['bundle_id']!=run['bundle_id']:raise ValueError('Wrong simulation bundle')
    folder=Path('data/local/bundles')/run['bundle_id']
    manifest=json.loads((folder/'manifest.json').read_text());g=manifest['grid']
    if sim['grid']!=g:raise ValueError('Simulation grid mismatch')
    shape=(g['ny'],g['nx'])
    z=np.fromfile(folder/'z.bin',dtype='<f4').reshape(shape)
    solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(shape)
    frames=sim['frames']
    integrity=validate_replay(frames,shape,solid,protocol['duration_s'],cell_area_m2=g['dx_m']*g['dy_m'])
    if len(frames)!=121 or abs(frames[-1]['time_s']-protocol['duration_s'])>1e-5:
        raise ValueError('Incomplete event replay')
    residuals=[f['ledger']['relative_residual'] for f in frames]
    if not np.isfinite(residuals).all():raise ValueError('Nonfinite mass ledger')
    peak=np.array(frames[-1]['maxDepth']).reshape(shape)
    features=[];unlocatable=[]
    for mark in marks:
        if mark['event_id']!=protocol['stn_event_id']:raise ValueError('Wrong observation event')
        # Unknown CRS cannot be presumed outside the domain or silently dropped.
        if mark.get('hdatum_id') not in crs_by_id:
            unlocatable.append({'id': mark['hwm_id'],'horizontal_datum_id': mark.get('hdatum_id'),
                'status': 'unknown_horizontal_datum_domain_membership_unresolved'})
            continue
        src_crs=crs_by_id[mark['hdatum_id']]
        coordinates=[mark['longitude_dd'],mark['latitude_dd']]
        x,y=Transformer.from_crs(src_crs,g['crs'],always_xy=True).transform(*coordinates)
        if not(g['origin_x_m']<=x<g['origin_x_m']+g['nx']*g['dx_m'] and
               g['origin_y_m']<=y<g['origin_y_m']+g['ny']*g['dy_m']):continue
        unavailable='vertical_datum_unresolved' if mark.get('vdatum_id')!=2 else 'measured_elevation_unavailable' if mark.get('elev_ft') is None else None
        lon,lat=Transformer.from_crs(src_crs,4326,always_xy=True).transform(*coordinates)
        description=mark.get('hwm_locationdescription') or ''
        transferred=any(phrase in description.lower() for phrase in ('transferred out of building','transferred out of the building'))
        reviewed=review[str(mark['hwm_id'])] if review is not None else None
        features.append({'type': 'Feature','geometry': {'type': 'Point','coordinates': [lon,lat]},'properties': {
            'id': mark['hwm_id'],'site_id': mark['site_id'],'quality': mark['hwm_quality_id'],
            'quality_description': quality[mark['hwm_quality_id']],'horizontal_crs': src_crs,
            'water_elevation_m': mark['elev_ft']*.3048 if unavailable is None else None,'location_description': description,
            'comparison_unavailable_reason': unavailable,'source_vertical_datum_id': mark.get('vdatum_id'),
            'interior': reviewed['eligibility']=='indoor' if reviewed else True if transferred or 'inside' in description.lower() else None,
            'observation_eligibility': reviewed['eligibility'] if reviewed else 'legacy_description_review',
            'eligibility_reason': reviewed['reason'] if reviewed else None,
            'observation_setting': 'building_mark_transferred_by_survey' if transferred else 'not_classified_from_description',
            'source_stillwater_flag': mark.get('stillwater'),
            'source_uncertainty_raw': mark.get('uncertainty'),
            'source_url': f"https://stn.wim.usgs.gov/STNServices/HWMs/{mark['hwm_id']}.json"}})
    result=compare_peak_elevations(manifest,peak,z,solid,features,'EPSG:4326',
        protocol['event_id'],protocol['event_id'],'NAVD88')
    for sample,feature in zip(result['samples'],features):
        sample.update({k:v for k,v in feature['properties'].items() if k not in ('id','water_elevation_m')})
        sample['distance_to_domain_edge_m']=min(sample['col']+.5,g['nx']-sample['col']-.5,
            sample['row']+.5,g['ny']-sample['row']-.5)*g['dx_m']
    gauge_peak=max(k['elevationM'] for k in run['levels'])+g['elevation_origin_m']
    result['site_balanced_metrics']=site_balanced_errors(result['samples'],gauge_peak)
    wet=[s for s in result['samples'] if s['status']=='compared']
    errors=np.array([gauge_peak-s['observed_elevation_m'] for s in wet])
    supported=[s for s in result['samples'] if s['status'] in ('compared','observed_flood_model_dry')]
    supported_errors=np.array([gauge_peak-s['observed_elevation_m'] for s in supported])
    result.update(grid_cells=n,cell_size_m=g['dx_m'],bundle_id=run['bundle_id'],
        replay_integrity=integrity,
        event_marks_with_unresolved_location=unlocatable,
        steps=sim['steps'],elapsed_s=sim['elapsedMs']/1000,renderer=sim['renderer'],
        max_recorded_relative_mass_residual=max(residuals),mass_gate_passed=max(residuals)<=.001,
        final_ledger=sim['ledger'],frames=len(frames),
        gauge_only_baseline={'peak_navd88_m': gauge_peak,'same_wet_point_count': len(wet),
            'rmse_m': float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
            'all_supported_point_count': len(supported),
            'all_supported_rmse_m': float(np.sqrt(np.mean(supported_errors**2))) if len(supported_errors) else None,
            'limitation': 'Gauge water elevation transferred to point coordinates; not an inundation or depth prediction. Same-wet score excludes modeled dry misses; all-supported score includes their observed elevations.'})
    if not result['mass_gate_passed']:result['status']='numerical_mass_gate_failed_accuracy_claim_rejected'
    runs.append(result)
    (root/f'observations-{n}.geojson').write_text(json.dumps({'type': 'FeatureCollection','features': features},indent=2))
audit={'event_id': protocol['event_id'],'protocol_sha256': protocol_hash,
    'assessment_software_sha256': {p:digest(Path(p)) for p in ('scripts/assess_historical_validation.py','services/reference/observations.py','services/reference/site_metrics.py','services/reference/replay_integrity.py')},
    'assessed_at': datetime.now(UTC).isoformat(),'runs': runs,'limitations': protocol['limitations'],
    'conclusion': 'Independent-source historical screening, not a strictly blinded validation. Sparse point maxima cannot establish city-wide flood depth, extent or timing skill.'}
if any(s.get('observation_setting')=='building_mark_transferred_by_survey' for r in runs for s in r['samples']):
    audit['limitations']=[*audit['limitations'], 'Some marks originated inside buildings and were transferred by survey. Their reported coordinates may identify the transferred survey location; the model omits indoor flooding. These are retained as screening comparisons, not direct outdoor depth validation. Raw source uncertainty is preserved without assuming its units or combining it into an error interval.']
(root/'accuracy.json').write_text(json.dumps(audit,indent=2))
(root/'source-checksums.json').write_text(json.dumps({**protocol['source_sha256'],
    **{str(root/f'simulation-{r["grid_cells"]}.json'):digest(root/f'simulation-{r["grid_cells"]}.json') for r in runs}},indent=2))
for r in runs:
    print(json.dumps({k:r[k] for k in ('grid_cells','compared_count','total_count','missed_flood_count','rmse_m','mass_gate_passed')}))
    print(json.dumps(r['samples'],indent=2))
