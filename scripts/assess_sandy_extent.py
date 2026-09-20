"""Compare preserved Sandy runs with NYC's HWM/DEM-derived inundation map."""
import hashlib
import json
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely import clip_by_rect
from shapely.geometry import box, mapping, shape
from shapely.ops import transform, unary_union

from services.reference.extent_comparison import mapped_flood_coverage

root=Path('artifacts/validation/sandy-2012')
protocol=json.loads((root/'protocol.json').read_text())
raw=json.loads((root/'inundation-extent.geojson').read_text())
runs=[];clipped_features=[]
for run in protocol['bundles']:
    folder=Path('data/local/bundles')/run['bundle_id']
    g=json.loads((folder/'manifest.json').read_text())['grid']
    n=run['grid_cells']
    bounds=(g['origin_x_m'],g['origin_y_m'],g['origin_x_m']+n*g['dx_m'],g['origin_y_m']+n*g['dy_m'])
    domain=box(*bounds)
    geographic=box(*Transformer.from_crs(g['crs'],4326,always_xy=True).transform_bounds(*bounds,densify_pts=21))
    forward=Transformer.from_crs(4326,g['crs'],always_xy=True)
    polys=[]
    for feature in raw['features']:
        if not feature.get('geometry'):raise ValueError('Reference geometry missing')
        geom=shape(feature['geometry'])
        # Reject distant polygons by cheap envelopes before validating large,
        # detailed regional geometries. Their vertices cannot affect this grid.
        if not box(*geom.bounds).intersects(geographic):continue
        geom=clip_by_rect(geom,*geographic.bounds)
        if geom.is_empty:continue
        if not geom.is_valid:geom=geom.buffer(0)
        if not geom.intersects(geographic):continue
        poly=transform(forward.transform,geom.intersection(geographic)).intersection(domain)
        if poly.is_empty:continue
        polys.append(poly)
        if n==64:clipped_features.append({'type': 'Feature','geometry': mapping(poly),'properties': feature['properties']})
    union=unary_union(polys)
    sim=json.loads((root/f'simulation-{n}.json').read_text())
    peak=np.array(sim['frames'][-1]['maxDepth']).reshape(n,n)
    initial=np.array(sim['frames'][0]['depth']).reshape(n,n)
    solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(n,n)
    metrics=mapped_flood_coverage(g,peak,solid,union,initial)
    runs.append(dict(grid_cells=n,bundle_id=run['bundle_id'],**metrics))
    print(n,{k:round(v,3) for k,v in metrics.items() if isinstance(v,float)},flush=True)
result={'reference_url': 'https://data.cityofnewyork.us/Environment/Sandy-Inundation-Zone/uyj8-7rv5',
    'data_url': 'https://data.cityofnewyork.us/resource/5xsi-dfpx.geojson',
    'reference_sha256': hashlib.sha256((root/'inundation-extent.geojson').read_bytes()).hexdigest(),
    'provenance': 'NYC-published field-verified extent derived from USGS HWM/surge sensors and NYC OEM 1 m DEM. Not independent of the point evidence. Source comments state clipping to a 1000 ft HSIP buffer.',
    'status': 'mapped_extent_diagnostic_not_observed_extent_validation','runs': runs}
(root/'extent-comparison.json').write_text(json.dumps(result,indent=2))
(root/'inundation-domain.geojson').write_text(json.dumps({'type': 'FeatureCollection',
    'crs': {'type': 'name','properties': {'name': 'EPSG:32618'}},'features': clipped_features}))
