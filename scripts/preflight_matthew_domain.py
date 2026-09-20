"""Prepare a controlled domain-size experiment without changing the core inputs."""
import hashlib
import json
from pathlib import Path

import httpx
import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.warp import Resampling, reproject

from services.geodata.providers import buildings

parent=Path('artifacts/validation/matthew-2016');root=Path('artifacts/validation/matthew-2016-domain4km')
root.mkdir(exist_ok=True)
if (root/'protocol.json').exists():raise ValueError('Experiment already frozen')
protocol=json.loads((parent/'protocol.json').read_text());design=json.loads((parent/'design.json').read_text())
old=next(r for r in protocol['bundles'] if r['grid_cells']==64);bundle=Path('data/local/bundles')/old['bundle_id']
manifest=json.loads((bundle/'manifest.json').read_text());g=manifest['grid'];cx=g['origin_x_m']+1000;cy=g['origin_y_m']+1000
plan={'experiment': 'Domain-size diagnostic after exposed Matthew results','parent_directory': parent.as_posix(),
    'baseline_extent_m': 2000,'candidate_extent_m': 4000,'baseline_grid': 64,'candidate_grid': 128,'cell_size_m': 31.25,
    'center': protocol['center'],'original_solver_unchanged': True,'positivity_candidate_enabled': False,
    'fixed_cohort': [16663,16667,16664,16723,16666],
    'required_core_invariants': ['bitwise bed elevations relative to the SAME original vertical origin','bitwise solid mask','identical physical forcing time series','identical roughness, rainfall, storage and infiltration'],
    'purpose': 'Move artificial edges one kilometre farther from the original domain while retaining its exact cell inputs. This changes the outer domain and initial connected water, not cell spacing.',
    'interpretation': 'Development diagnostic only. No default adoption or untouched-event claim. Retain all original five marks and report extra-domain observation metadata separately.',
    'limitation': 'One measured east reservoir still approximates spatial water-level variation; enlarging the domain does not validate that boundary model.'}
(root/'design-plan.json').write_text(json.dumps(plan,indent=2))
bounds=Transformer.from_crs(g['crs'],4269,always_xy=True).transform_bounds(cx-2100,cy-2100,cx+2100,cy+2100,densify_pts=21)
base='https://www.ngdc.noaa.gov/thredds/wcs/'+design['terrain_dataset']
params={'service': 'WCS','version': '1.0.0','request': 'GetCoverage','coverage': design['terrain_coverage'],'format': 'GeoTIFF_Float','crs': 'OGC:CRS84','bbox': ','.join(map(str,bounds))}
url=str(httpx.Request('GET',base,params=params).url);path=root/'noaa-topobathy-subset.tif'
if not path.exists():
    with httpx.Client(timeout=120,follow_redirects=True) as client, client.stream('GET',url) as response:
        response.raise_for_status();chunks=[];size=0
        for chunk in response.iter_bytes():
            size+=len(chunk)
            if size>20_000_000:raise ValueError('Terrain subset exceeds 20 MB')
            chunks.append(chunk)
    path.write_bytes(b''.join(chunks))
with rasterio.open(path) as src:
    out=np.full((128,128),np.nan,dtype='f4')
    reproject(src.read(1),out,src_transform=src.transform,src_crs='EPSG:4269',src_nodata=src.nodata,
        dst_transform=Affine(31.25,0,cx-2000,0,-31.25,cy+2000),dst_crs=g['crs'],dst_nodata=np.nan,resampling=Resampling.bilinear)
    if not np.isfinite(out).all():raise ValueError('Incomplete terrain')
    out=np.flipud(out);np.save(root/'topobathy-128.npy',out)
original=np.fromfile(bundle/'z.bin',dtype='<f4').reshape(64,64)
core=(out.astype(float)-g['elevation_origin_m']).astype('f4')[32:96,32:96]
geometry_bounds=Transformer.from_crs(g['crs'],4326,always_xy=True).transform_bounds(cx-2000,cy-2000,cx+2000,cy+2000,densify_pts=21)
footprints=root/'current-buildings.geojson'
if not footprints.exists():
    features,sources=buildings(geometry_bounds)
    footprints.write_text(json.dumps({'type': 'FeatureCollection','features': features}))
    (root/'building-sources.json').write_text(json.dumps(sources,indent=2))
rows=[]
# Coordinate-only inventory: measured heights in the wider domain remain unused.
for m in json.loads((parent/'hwms.json').read_text()):
    datum={2:4269,3:4267,4:4326}.get(m.get('hdatum_id'))
    if datum is None:continue
    x,y=Transformer.from_crs(datum,g['crs'],always_xy=True).transform(m['longitude_dd'],m['latitude_dd'])
    if cx-2000<=x<cx+2000 and cy-2000<=y<cy+2000:
        rows.append({'id': m['hwm_id'],'site_id': m['site_id'],'original_cohort': m['hwm_id'] in plan['fixed_cohort'],
            'role': 'fixed_comparison_cohort' if m['hwm_id'] in plan['fixed_cohort'] else 'outside_original_domain_not_scored_in_controlled_comparison'})
(root/'observation-inventory.json').write_text(json.dumps({'marks': rows,'scope': 'Coordinates and IDs only; no additional HWM heights read or displayed'},indent=2))
result={'request_url': url,'terrain_dataset': design['terrain_dataset'],'vertical_datum': 'NAVD88','horizontal_crs': 'EPSG:4269',
    'terrain_subset_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'native_resampling_core_max_difference_m': float(np.max(np.abs(core-original))),
    'core_policy': 'Before freezing, retain the original bed array exactly in the shared core; record the native resampling difference explicitly. No observations used to modify bed.',
    'original_vertical_origin_m': g['elevation_origin_m'],'range_m': [float(out.min()),float(out.max())],
    'outside_original_cohort_count': sum(not r['original_cohort'] for r in rows)}
(root/'preflight.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
