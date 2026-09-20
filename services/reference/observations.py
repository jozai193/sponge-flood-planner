"""Compare event-matched peak depths with sourced point observations."""
import numpy as np
from pyproj import Transformer


def compare_peak_elevations(manifest, peak_depth, bed_local, solid, features,
                            observation_crs, model_event_id, observation_event_id,
                            observation_datum, wet_threshold_m=.01):
    """Audit absolute peak-water observations without treating dry ground as water.

    Inputs are metres. Bed uses the manifest's local offset; observations use the
    explicitly matching vertical datum. No nearest-wet-cell relocation is allowed.
    """
    if not model_event_id or model_event_id != observation_event_id:
        raise ValueError('An identical explicit event ID is required')
    grid = manifest['grid']
    datum = grid.get('vertical_datum')
    if datum not in ('NAVD88',) or observation_datum != datum:
        raise ValueError('A supported matching vertical datum is required')
    if grid.get('row_direction') != 'north':
        raise ValueError('Unsupported model row orientation')
    offset = grid.get('elevation_origin_m')
    if offset is None or not np.isfinite(offset):
        raise ValueError('Explicit finite local elevation offset required')
    if not np.isfinite(wet_threshold_m) or wet_threshold_m <= 0:
        raise ValueError('Positive wet threshold required')
    peak, bed, mask = np.asarray(peak_depth), np.asarray(bed_local), np.asarray(solid)
    shape = (grid['ny'], grid['nx'])
    if (peak.shape != shape or bed.shape != shape or mask.shape != shape
            or not np.isfinite(peak).all() or not np.isfinite(bed).all()
            or np.any(peak < 0) or not np.isin(mask, [0, 1]).all()):
        raise ValueError('Invalid model arrays')
    transform = Transformer.from_crs(observation_crs, grid['crs'], always_xy=True)
    rows = []
    for index, feature in enumerate(features):
        geom, props = feature.get('geometry', {}), feature.get('properties', {})
        if geom.get('type') != 'Point':
            raise ValueError('Point observations required')
        observed = props.get('water_elevation_m')
        unavailable = props.get('comparison_unavailable_reason')
        if unavailable is not None and (unavailable not in ('vertical_datum_unresolved','measured_elevation_unavailable') or observed is not None):
            raise ValueError('Unavailable comparison requires an explicit supported reason and no datum-assumed elevation')
        if unavailable is None and (observed is None or not np.isfinite(observed)):
            raise ValueError('Finite measured water_elevation_m required')
        x, y = transform.transform(*geom['coordinates'][:2])
        if not np.isfinite([x, y]).all():
            raise ValueError('Invalid transformed observation')
        col = int(np.floor((x-grid['origin_x_m'])/grid['dx_m']))
        row = int(np.floor((y-grid['origin_y_m'])/grid['dy_m']))
        item = {'index': index, 'observation_id': props.get('id', index),
                    'site_id': props.get('site_id'), 'observed_elevation_m': float(observed) if observed is not None else None,
                    'quality': props.get('quality'), 'row': row, 'col': col}
        rows.append(item)
        if not (0 <= row < shape[0] and 0 <= col < shape[1]):
            item['status'] = 'outside_domain'
            continue
        ground, depth = float(bed[row, col]+offset), float(peak[row, col])
        item.update(ground_elevation_m=ground, simulated_peak_depth_m=depth,
                    observation_below_model_ground=bool(observed < ground) if observed is not None else None)
        if unavailable:
            item['status'] = unavailable
        elif mask[row, col]:
            item['status'] = 'building_cell_unresolved'
        elif props.get('interior', False):
            item['status'] = 'interior_observation_unsupported'
        elif props.get('observation_eligibility') == 'unresolved':
            item['status'] = 'observation_setting_unresolved'
        elif depth <= wet_threshold_m:
            item['status'] = 'observed_flood_model_dry'
        else:
            item.update(status='compared', predicted_elevation_m=ground+depth,
                        error_m=ground+depth-float(observed))
    compared = [r for r in rows if r['status'] == 'compared']
    errors = np.array([r['error_m'] for r in compared])
    return {'event_id': model_event_id, 'vertical_datum': datum, 'samples': rows,
                'compared_count': len(compared), 'total_count': len(rows),
                'unique_compared_sites': len({r['site_id'] for r in compared if r['site_id'] is not None}),
                'missed_flood_count': sum(r['status']=='observed_flood_model_dry' for r in rows),
                'rmse_m': float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
                'mae_m': float(np.abs(errors).mean()) if len(errors) else None,
                'bias_m': float(errors.mean()) if len(errors) else None,
                'status': 'retrospective_screening_comparison_not_site_validation',
                'limitation': 'Error statistics cover wet comparable cells only; dry misses, building cells, repeated sites and terrain conflicts must be reported separately.'}


def compare_peak_depths(manifest,peak_depth,features,observation_crs,model_event_id,observation_event_id):
    if not model_event_id or model_event_id!=observation_event_id:
        raise ValueError('An identical explicit event ID is required; acquisition dates are not flood event IDs')
    grid=manifest['grid'];peak=np.asarray(peak_depth,dtype=float)
    if peak.shape!=(grid['ny'],grid['nx']) or not np.isfinite(peak).all() or np.any(peak<0):
        raise ValueError('Invalid model peak-depth grid')
    transform=Transformer.from_crs(observation_crs,grid['crs'],always_xy=True)
    rows=[];excluded=[]
    for index,feature in enumerate(features):
        geom=feature.get('geometry',{});props=feature.get('properties',{})
        if geom.get('type')!='Point':raise ValueError('Observation comparison requires point geometries')
        depth=props.get('depth_m')
        if depth is None or not np.isfinite(depth) or depth<0:
            raise ValueError('Measured depth above local ground is required; absolute water elevation is not depth')
        x,y=transform.transform(*geom['coordinates'][:2])
        if not np.isfinite([x,y]).all():raise ValueError('Invalid transformed observation')
        col=int(np.floor((x-grid['origin_x_m'])/grid['dx_m']))
        row=int(np.floor((y-grid['origin_y_m'])/grid['dy_m']))
        if grid.get('row_direction')!='north':raise ValueError('Unsupported model row orientation')
        if not (0<=row<grid['ny'] and 0<=col<grid['nx']):
            excluded.append(index);continue
        prediction=float(peak[row,col]);rows.append({'index': index,'observed_depth_m': depth,'predicted_depth_m': prediction,'error_m': prediction-depth})
    if not rows:raise ValueError('No observations intersect the simulation grid')
    errors=np.array([r['error_m'] for r in rows])
    return {'event_id': model_event_id,'count': len(rows),'excluded_outside': excluded,
        'bias_m': float(errors.mean()),'mae_m': float(np.abs(errors).mean()),'rmse_m': float(np.sqrt(np.mean(errors**2))),
        'samples': rows,'status': 'comparison_only_not_calibration',
        'limitation': 'Point depth and cell-average peak depth have different spatial support; source uncertainty and timing still require review.'}
