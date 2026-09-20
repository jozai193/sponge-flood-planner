"""Compare untouched Sandy outputs with USGS marks; keep exclusions visible."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from pyproj import Transformer

from services.reference.observations import compare_peak_elevations

ROOT=Path('artifacts/validation/sandy-2012')
protocol=json.loads((ROOT/'protocol.json').read_text())
if hashlib.sha256((ROOT/'protocol.json').read_bytes()).hexdigest() != (ROOT/'protocol.sha256').read_text():
    raise ValueError('Protocol changed after freezing')
marks=json.loads((ROOT/'hwms.json').read_text())
quality={r['hwm_quality_id']:r for r in json.loads((ROOT/'quality-lookup.json').read_text())}
results=[]
for run in protocol['bundles']:
    path=ROOT/f"simulation-{run['grid_cells']}.json"
    if not path.exists():continue
    simulation=json.loads(path.read_text())
    folder=Path('data/local/bundles')/run['bundle_id']
    manifest=json.loads((folder/'manifest.json').read_text())
    g=manifest['grid'];shape=(g['ny'],g['nx'])
    z=np.fromfile(folder/'z.bin',dtype='<f4').reshape(shape)
    solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(shape)
    peak=np.array(simulation['frames'][-1]['maxDepth']).reshape(shape)
    features=[]
    transform=Transformer.from_crs(4269,g['crs'],always_xy=True)
    for mark in marks:
        x,y=transform.transform(mark['longitude_dd'],mark['latitude_dd'])
        if not(g['origin_x_m']<=x<g['origin_x_m']+g['nx']*g['dx_m'] and
               g['origin_y_m']<=y<g['origin_y_m']+g['ny']*g['dy_m']):continue
        if mark['event_id']!=24 or mark['vdatum_id']!=2 or mark['hdatum_id']!=2:
            raise ValueError('Unexpected event or horizontal/vertical datum among selected marks')
        features.append({'type':'Feature','geometry':{'type':'Point','coordinates':[mark['longitude_dd'],mark['latitude_dd']]},
            'properties':{'id':mark['hwm_id'],'site_id':mark['site_id'],'quality':mark['hwm_quality_id'],
                'quality_description':quality[mark['hwm_quality_id']]['hwm_quality'],
                'horizontal_crs':'EPSG:4269',
                'horizontal_method':'Map (digital or paper)' if mark.get('hcollect_method_id')==4 else str(mark.get('hcollect_method_id')),
                'water_elevation_m':mark['elev_ft']*.3048,
                'location_description':mark['hwm_locationdescription'],
                'interior':'inside' in mark['hwm_locationdescription'].lower(),
                'source_url':f"https://stn.wim.usgs.gov/STNServices/HWMs/{mark['hwm_id']}.json"}})
    result=compare_peak_elevations(manifest,peak,z,solid,features,'EPSG:4269',
        protocol['event_id'],protocol['event_id'],'NAVD88')
    for sample,feature in zip(result['samples'],features):
        sample.update({k:v for k,v in feature['properties'].items() if k not in ('water_elevation_m','id')})
    # A better-quality subset is reported as well as all marks; no exclusions are hidden.
    primary=[r for r in result['samples'] if r['status']=='compared' and r['quality']<=3]
    errors=np.array([r['error_m'] for r in primary])
    result['excellent_good_fair_subset']={'count':len(primary),'ids':[r['observation_id'] for r in primary],
        'rmse_m':float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
        'mae_m':float(np.abs(errors).mean()) if len(errors) else None,
        'bias_m':float(errors.mean()) if len(errors) else None}
    gauge_peak=max(k['elevationM'] for k in run['levels'])+g['elevation_origin_m']
    wet=[r for r in result['samples'] if r['status']=='compared']
    gauge_errors=np.array([gauge_peak-r['observed_elevation_m'] for r in wet])
    result['gauge_only_baseline']={'peak_navd88_m':gauge_peak,'same_wet_point_count':len(wet),
        'rmse_m':float(np.sqrt(np.mean(gauge_errors**2))) if len(gauge_errors) else None,
        'meaning':'Transfer the measured gauge peak unchanged to each comparable mark. This checks whether local model agreement adds value beyond the supplied boundary level; it predicts no inundation extent.'}
    frames=simulation['frames']
    max_residual=max(f['ledger']['relative_residual'] for f in frames)
    if abs(frames[-1]['time_s']-protocol['duration_s'])>1e-5:
        raise ValueError('Incomplete physical event duration')
    result.update(grid_cells=run['grid_cells'],cell_size_m=g['dx_m'],bundle_id=run['bundle_id'],
        elapsed_s=simulation['elapsedMs']/1000,steps=simulation['steps'],renderer=simulation['renderer'],
        max_recorded_relative_mass_residual=max_residual,mass_gate_passed=max_residual<=.001,
        final_ledger=simulation['ledger'],frames=len(frames))
    if not result['mass_gate_passed']:
        result['status']='numerical_mass_gate_failed_accuracy_claim_rejected'
    results.append(result)
    (ROOT/f"observations-{run['grid_cells']}.geojson").write_text(json.dumps({'type':'FeatureCollection','crs':{'type':'name','properties':{'name':'EPSG:4269'}},'features':features},indent=2))
comparison={'event_id':protocol['event_id'],'assessed_at':datetime.now(UTC).isoformat(),
    'protocol_sha256':(ROOT/'protocol.sha256').read_text(),'runs':results,'limitations':protocol['limitations'],
    'conclusion':'This is a limited retrospective screening test. Point water-level agreement does not establish inundation extent, flood depth, timing or city-wide hazard accuracy.'}
comparison['limitations']=list(protocol['limitations'])+[
    'The selected USGS observation coordinates use NAD83 (EPSG:4269), transformed explicitly to the model grid.',
    'Selected mark positions were located from digital or paper maps, not surveyed GNSS positions. HWM quality labels describe vertical mark identification, not exact map-to-cell positioning.',
    'A pre-event NYC 2010 terrain archive was located after freezing this experiment; it was not substituted. Its main raster expands to roughly 99 GB.'
]
if len(results)==2:
    a={r['observation_id']:r for r in results[0]['samples'] if r['status']=='compared'}
    b={r['observation_id']:r for r in results[1]['samples'] if r['status']=='compared'}
    common=sorted(a.keys()&b.keys())
    comparison['grid_comparison']={'common_wet_ids':common,
        'common_point_rmse_m':{str(r['grid_cells']):float(np.sqrt(np.mean([s['error_m']**2 for s in r['samples'] if s['observation_id'] in common]))) for r in results} if common else {},
        'max_peak_elevation_difference_m':max((abs(a[i]['predicted_elevation_m']-b[i]['predicted_elevation_m']) for i in common),default=None),
        'limitation':'Two grids are a sensitivity check, not a three-grid convergence study; footprint rasterisation changes between grids.'}
(ROOT/'accuracy.json').write_text(json.dumps(comparison,indent=2))
lines=['# Sandy 2012 retrospective screening test','',
    '**This test does not validate SPONGE for real coastal hazard prediction.**','',
    'The unchanged production WebGL2 HLL solver was driven by 18 hours of verified NOAA total water levels at The Battery, from 2012-10-29 12:00 UTC to 2012-10-30 06:00 UTC. The domain is a fixed 1 km square at Battery Park City / the Hudson waterfront. No rainfall, infrastructure design, or observational tuning was applied.','',
    'The boundary and terrain use NAVD88 metres with an explicit numerical offset; USGS mark coordinates use NAD83. All event marks in the domain are audited, including dry predictions and unresolved current-building cells.','',
    '| Grid | Wet comparable marks | Observed locations modelled dry | Wet-cell RMSE (m) | Gauge-only reference RMSE (m) | Numerical mass gate |',
    '| --- | ---: | ---: | ---: | ---: | --- |']
fmt=lambda v:'unavailable' if v is None else f'{v:.3f}'
for r in results:
    lines.append(f"| {r['grid_cells']} x {r['grid_cells']} ({r['cell_size_m']:.3f} m) | {r['compared_count']}/{r['total_count']} | {r['missed_flood_count']} | {fmt(r['rmse_m'])} | {fmt(r['gauge_only_baseline']['rmse_m'])} | {'passed' if r['mass_gate_passed'] else 'FAILED'} |")
lines+=['','RMSE is computed only where the model is wet and the observation is comparable. It cannot conceal the separately reported dry and unresolved locations. The gauge-only reference transfers the supplied gauge peak directly to each comparable point; similar performance indicates that local routing skill has not been established.','',
        'The grids do not have identical comparable-point sets. On the four common wet points, RMSE is '+str(comparison.get('grid_comparison',{}).get('common_point_rmse_m',{}))+' metres. Two grids do not establish convergence.','',
        '## Individual observations','']
for r in results:
    lines += [f"### {r['grid_cells']} x {r['grid_cells']}",'',
        '| USGS mark | Quality | Observed m NAVD88 | Model m NAVD88 | Error m | Status |',
        '| --- | --- | ---: | ---: | ---: | --- |']
    for s in r['samples']:
        status=s['status'].replace('_',' ')+(' (observation below model ground)' if s.get('observation_below_model_ground') else '')
        lines.append(f"| {s['observation_id']} | {s['quality_description']} | {fmt(s['observed_elevation_m'])} | {fmt(s.get('predicted_elevation_m'))} | {fmt(s.get('error_m'))} | {status} |")
    lines+=['',f"Completed {r['steps']:,} physical timesteps in {r['elapsed_s']:.1f} seconds. Maximum recorded relative water-balance residual: {100*r['max_recorded_relative_mass_residual']:.6f}%. Sampling points are correlated; unique comparable sites: {r['unique_compared_sites']}.",'']
lines+=['## Interpretation and limits','']+[f'- {s}' for s in comparison['limitations']]
lines+=['','A passing mass-balance test demonstrates numerical bookkeeping, not site accuracy. No wet/dry inundation-extent observations or observed timing series were used as validation targets. A meaningful next validation requires event-era geometry, bathymetry, relevant sewer and wave processes, more independent points, and a mapped wet/dry extent.','',
    '## Reproduce and inspect','',
    'Raw provider records, the frozen protocol, two immutable bundles, exact input identities, full-precision solver frames and source checksums accompany this assessment. Display figures round values; numerical comparisons use original outputs.','',
    'Run `node scripts/run-sandy-validation.mjs`, then `python -m scripts.assess_sandy_validation`, `python -m scripts.plot_sandy_validation`, and `python -m scripts.render_sandy_validation` in the prepared workspace.','',
    '- [USGS event 24 observations](https://stn.wim.usgs.gov/STNServices/Events/24/HWMs.json)',
    '- [USGS Sandy monitoring report](https://pubs.usgs.gov/of/2013/1043/)',
    '- [NOAA forcing request]('+protocol['forcing_url']+')',
    '- [USGS terrain metadata](https://www.sciencebase.gov/catalog/item/5eacfcc382cefae35a25102c)',
    '- [USGS high-water-mark uncertainty guidance](https://www.usgs.gov/mission-areas/water-resources/science/high-water-marks)',
    '- [Pre-event NYC 2010 terrain metadata](https://github.com/CityOfNewYork/nyc-geo-metadata/blob/main/Metadata/Metadata_2010_DEM.md)','']
(ROOT/'report.md').write_text('\n'.join(lines),encoding='utf-8')
sources=[]
for path in ROOT.iterdir():
    if path.is_file() and path.suffix in ('.json','.geojson','.txt') and not path.name.startswith(('simulation','accuracy','progress','source-checksums')):
        sources.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
(ROOT/'source-checksums.json').write_text(json.dumps(sources,indent=2))
print(json.dumps([{k:r[k] for k in ['grid_cells','compared_count','missed_flood_count','rmse_m','excellent_good_fair_subset','mass_gate_passed']} for r in results],indent=2))
