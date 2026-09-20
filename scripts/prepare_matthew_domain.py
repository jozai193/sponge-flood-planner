"""Freeze a simulation-only larger domain with bitwise-identical shared inputs."""
import copy
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.features import rasterize
from shapely.geometry import box, shape
from shapely.ops import transform

from services.api.contracts import content_hash

root=Path('artifacts/validation/matthew-2016-domain4km');parent=Path('artifacts/validation/matthew-2016')
if (root/'protocol.json').exists():raise ValueError('Protocol already frozen')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((parent/'protocol.json').read_text());plan=json.loads((root/'design-plan.json').read_text())
for name,digest in p['source_sha256'].items():
    if sha(Path(name))!=digest:raise ValueError('Parent input changed: '+name)
old=next(r for r in p['bundles'] if r['grid_cells']==64);old_folder=Path('data/local/bundles')/old['bundle_id']
old_manifest=json.loads((old_folder/'manifest.json').read_text());g=copy.deepcopy(old_manifest['grid'])
old_z=np.fromfile(old_folder/'z.bin',dtype='<f4').reshape(64,64);old_solid=np.fromfile(old_folder/'solid.bin',dtype='u1').reshape(64,64)
g.update(nx=128,ny=128,origin_x_m=g['origin_x_m']-1000,origin_y_m=g['origin_y_m']-1000)
# Source pixels in the overlap must be identical before we retain the old warp.
with rasterio.open(parent/'noaa-topobathy-subset.tif') as a,rasterio.open(root/'noaa-topobathy-subset.tif') as b:
    col=round((a.transform.c-b.transform.c)/a.transform.a);row=round((b.transform.f-a.transform.f)/a.transform.a)
    overlap=b.read(1)[row:row+a.height,col:col+a.width]
    if not np.array_equal(a.read(1),overlap):raise ValueError('Native source overlap differs')
absolute=np.load(root/'topobathy-128.npy').astype(float)
z=(absolute-g['elevation_origin_m']).astype('<f4');unmatched=z[32:96,32:96].copy()
z[32:96,32:96]=old_z
to_grid=Transformer.from_crs(4326,g['crs'],always_xy=True)
extent=box(g['origin_x_m'],g['origin_y_m'],g['origin_x_m']+4000,g['origin_y_m']+4000)
polygons=[]
for feature in json.loads((root/'current-buildings.geojson').read_text())['features']:
    geom=transform(to_grid.transform,shape(feature['geometry']))
    if not geom.is_valid:geom=geom.buffer(0)
    geom=geom.intersection(extent)
    if geom.is_empty or geom.area<4 or geom.geom_type not in ('Polygon','MultiPolygon'):continue
    polygons.append((geom,1))
solid=rasterize(polygons,out_shape=(128,128),transform=Affine(31.25,0,g['origin_x_m'],0,31.25,g['origin_y_m']),fill=0,dtype='uint8')
if not np.array_equal(solid[32:96,32:96],old_solid):raise ValueError('Expanded footprints change the original solid mask; do not run')
arrays={'z':z,'solid':solid,**{name:np.zeros((128,128),dtype='<f4') for name in ('rain_weights','soil_capacity','infiltration')},'roughness':np.full((128,128),.035,dtype='<f4')}
artifacts=[{'name': name,'dtype': str(value.dtype),'shape': [128,128],'bytes': value.nbytes,'sha256': hashlib.sha256(value.tobytes()).hexdigest()} for name,value in arrays.items()]
identity={'validation_fixture': 'domain-extension-v1','parent_bundle': old['bundle_id'],'grid': g,'artifacts': artifacts}
bundle_id=content_hash(identity);folder=Path('data/local/bundles')/bundle_id
if folder.exists():raise ValueError('Refusing to replace fixture bundle')
folder.mkdir()
for name,value in arrays.items():(folder/f'{name}.bin').write_bytes(value.tobytes())
manifest={'schema_version': 'sponge.v1','bundle_id': bundle_id,'label': 'Scientific domain test only: Matthew 4 km',
    'location': p['center'],'extent_m': 4000,'grid': g,'buildings': [],'candidates': [],'artifacts': artifacts,
    'sources': old_manifest['sources']+json.loads((root/'building-sources.json').read_text()),
    'quality': {'validation_only': True,'planning_supported': False,'observation_validation': 'not_yet_compared',
        'building_representation': 'Raster solid mask; individual display geometry omitted from scientific fixture'},
    'assumptions': ['Scientific coastal fixture; no planning candidates, losses or rainfall allocation.',
        'Original 2 km bed and mask retained bitwise; outer terrain and footprints from unchanged source products.',
        'Same source pixels, different warp extents produce slightly different resampling. Original shared-core warp retained explicitly.']}
manifest['content_hash']=content_hash(manifest);(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
first=old['levels'][0]['elevationM'];peak=max(k['elevationM'] for k in old['levels'])
edge=z[:,-1];edge_mask=solid[:,-1]==0
if not edge_mask.any():raise ValueError('No exposed east reservoir cells')
check={'core_bed_bitwise_equal': np.array_equal(z[32:96,32:96],old_z),'core_solid_bitwise_equal': True,
    'native_overlap_bitwise_equal': True,'cell_spacing_m': 31.25,'vertical_origin_unchanged': True,
    'pre_preservation_core_warp_difference_m': float(np.max(np.abs(unmatched-old_z))),
    'east_edge': {'exposed_cells': int(edge_mask.sum()),'below_initial': int(np.sum(edge[edge_mask]<first)),'below_peak': int(np.sum(edge[edge_mask]<peak)),
        'bed_navd88_range': [float(edge[edge_mask].min()+g['elevation_origin_m']),float(edge[edge_mask].max()+g['elevation_origin_m'])]},
    'limitation': 'Core warp is deliberately preserved. The extension seam and initial connected-water change remain part of the domain experiment; this is not independent terrain validation.'}
(root/'core-integrity.json').write_text(json.dumps(check,indent=2))
cohort=set(plan['fixed_cohort']);raw=json.loads((parent/'hwms.json').read_text())
selected=[mark for mark in raw if mark['hwm_id'] in cohort]
if {mark['hwm_id'] for mark in selected}!=cohort:raise ValueError('Incomplete fixed cohort')
(root/'hwms.json').write_text(json.dumps(selected))
shutil.copy2(parent/'observation-review.json',root/'observation-review.json')
rules={'frozen_before_simulation': True,'observations_already_exposed': True,'common_point_and_site_rmse_worsening_tolerance_m': .01,
    'no_lost_supported_or_wet_points': True,'no_increased_dry_misses': True,'require_replay_and_mass_integrity': True,
    'explanation': 'Domain diagnostic at fixed 31.25 m cell size. A passing development check requires another event before any adoption.'}
(root/'evaluation-plan.json').write_text(json.dumps(rules,indent=2))
p.update(created_at=datetime.now(UTC).isoformat(),extent_m=4000,grid_sizes=[128],bundles=[{'grid_cells': 128,'bundle_id': bundle_id,'levels': old['levels']}],
    experiment='fixed-cell-spacing-domain-extension',parent_directory=parent.as_posix(),parent_protocol_sha256=sha(parent/'protocol.json'),
    selection='Retain original five exposed marks for same-cohort domain comparison. Wider-area coordinate inventory is reported separately. No new observation outcomes used.',
    limitations=p['limitations']+manifest['assumptions']+['A larger one-edge-reservoir domain does not establish correct harbour forcing.'])
paths=[root/name for name in ('design-plan.json','evaluation-plan.json','core-integrity.json','observation-inventory.json','hwms.json','observation-review.json','current-buildings.geojson','building-sources.json','preflight.json','noaa-topobathy-subset.tif')]
paths += [folder/'manifest.json',folder/'z.bin',folder/'solid.bin']
paths += [Path(name) for name in ('scripts/prepare_matthew_domain.py','scripts/run-historical-validation.mjs','scripts/assess_historical_validation.py','scripts/compare_domain_experiment.py','services/reference/replay_integrity.py','services/reference/observations.py','services/reference/site_metrics.py','services/reference/validation_regression.py')]
for path in paths:p['source_sha256'][path.as_posix()]=sha(path)
(root/'protocol.json').write_text(json.dumps(p,indent=2));(root/'protocol.sha256').write_text(sha(root/'protocol.json'))
print(json.dumps(check,indent=2));print('Frozen',root)
