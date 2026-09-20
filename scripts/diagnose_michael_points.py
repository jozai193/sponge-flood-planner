"""Diagnose fixed historical point discrepancies without moving or fitting marks."""
import hashlib
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds

root = Path(sys.argv[1]) if len(sys.argv)>1 else Path('artifacts/validation/michael-2018')
audit = json.loads((root/'accuracy.json').read_text())
protocol = json.loads((root/'protocol.json').read_text())
run = protocol['bundles'][-1]
result = audit['runs'][-1]
folder = Path('data/local/bundles')/run['bundle_id']
g = json.loads((folder/'manifest.json').read_text())['grid']
shape = (g['ny'], g['nx'])
bed = np.fromfile(folder/'z.bin', dtype='<f4').reshape(shape)
solid = np.fromfile(folder/'solid.bin', dtype='u1').reshape(shape).astype(bool)
level = max(k['elevationM'] for k in run['levels'])
eligible = (bed < level) & ~solid
reached = np.zeros(shape, dtype=bool)
queue = deque()
edge = protocol['boundary_edge']
cells = [i for i in range(g['nx']*g['ny']) if not solid.flat[i] and
    (i % g['nx'] == 0 if edge == 'west' else i % g['nx'] == g['nx']-1 if edge == 'east' else
     i < g['nx'] if edge == 'south' else i >= (g['ny']-1)*g['nx'])]
for cell in cells:
    row, col = divmod(cell, g['nx'])
    if eligible[row, col]:
        reached[row, col] = True
        queue.append((row, col))
while queue:
    row, col = queue.popleft()
    for rr, cc in ((row-1,col),(row+1,col),(row,col-1),(row,col+1)):
        if 0 <= rr < g['ny'] and 0 <= cc < g['nx'] and eligible[rr,cc] and not reached[rr,cc]:
            reached[rr,cc] = True
            queue.append((rr,cc))
features = {f['properties']['id']: f for f in json.loads((root/f'observations-{run["grid_cells"]}.geojson').read_text())['features']}
source = json.loads((root/'topobathy-source.json').read_text())
rows = []
with rasterio.open(root/'noaa-topobathy-subset.tif') as src:
    # Original dataset metadata overrides the service's generic EPSG:4326 tag.
    tr = Transformer.from_crs(4326, source['horizontal_crs'], always_xy=True)
    to_grid = Transformer.from_crs(4326,g['crs'],always_xy=True)
    from_grid = Transformer.from_crs(g['crs'],source['horizontal_crs'],always_xy=True)
    for sample in result['samples']:
        x, y = tr.transform(*features[sample['observation_id']]['geometry']['coordinates'])
        native = float(next(src.sample([(x,y)], masked=True))[0])
        if not np.isfinite(native):
            raise ValueError('Missing native terrain at retained observation')
        row, col = sample['row'], sample['col']
        gx,gy=to_grid.transform(*features[sample['observation_id']]['geometry']['coordinates'])
        radius=g['dx_m']/2
        bounds=from_grid.transform_bounds(gx-radius,gy-radius,gx+radius,gy+radius,densify_pts=21)
        neighborhood=src.read(1,window=from_bounds(*bounds,src.transform),masked=True).compressed()
        neighborhood=neighborhood[np.isfinite(neighborhood)]
        screening_level = (sample['ground_elevation_m']+sample['simulated_peak_depth_m']) if not solid[row,col] and sample['simulated_peak_depth_m']>.01 else None
        item = {'observation_id': sample['observation_id'], 'status': sample['status'],
            'observed_navd88_m': sample['observed_elevation_m'],
            'native_ground_navd88_m': native,
            'model_ground_navd88_m': sample['ground_elevation_m'],
            'native_ground_above_observation_m': native-sample['observed_elevation_m'] if sample['observed_elevation_m'] is not None else None,
            'model_minus_native_ground_m': sample['ground_elevation_m']-native,
            'native_neighborhood': {'half_width_m': radius,'count': len(neighborhood),
                'min_m': float(neighborhood.min()) if len(neighborhood) else None,
                'median_m': float(np.median(neighborhood)) if len(neighborhood) else None,
                'max_m': float(neighborhood.max()) if len(neighborhood) else None},
            'gauge_peak_minus_observation_m': level+g['elevation_origin_m']-sample['observed_elevation_m'] if sample['observed_elevation_m'] is not None else None,
            'below_peak_connected_to_boundary': bool(reached[row,col]),
            'solid': bool(solid[row,col]),
            'predicted_peak_navd88_m': sample.get('predicted_elevation_m'),
            'grid_water_level_at_survey_coordinate_m': screening_level,
            'grid_level_minus_gauge_peak_m': screening_level-level-g['elevation_origin_m'] if screening_level is not None else None,
            'model_peak_minus_gauge_peak_m': (sample['predicted_elevation_m']-level-g['elevation_origin_m']) if 'predicted_elevation_m' in sample else None}
        rows.append(item)
out = {'assessment_sha256': hashlib.sha256((root/'accuracy.json').read_bytes()).hexdigest(),
    'method': 'Exact containing native pixel at unchanged observation coordinate; four-neighbor connectivity from frozen boundary cells below the supplied peak. No terrain replacement or observation relocation.',
    'limitations': ['Native terrain is the same source compilation used by the model, not independent ground truth.',
        'Connectivity at a constant peak omits duration, momentum and dynamic overtopping.',
        'The half-cell neighborhood is a terrain-support diagnostic, not a measured position uncertainty or alternative prediction sample.',
        'Gauge-to-mark differences can include spatial water-level variation, waves and observation uncertainty; they do not prove a single cause.'],
    'observations': rows}
(root/'point-diagnosis.json').write_text(json.dumps(out, indent=2))
print(json.dumps(rows, indent=2))
