"""Create a resolution-only candidate from preserved sources, without fitting."""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.warp import Resampling, reproject

source=Path(sys.argv[1]);destination=Path(sys.argv[2]);n=int(sys.argv[3])
if destination.exists():raise ValueError('Use a new candidate directory')
destination.mkdir(parents=True)
for name in ('hwms.json','observation-review.json','forcing-preflight.json','current-buildings.geojson','building-sources.json','terrain-metadata.das','topobathy-source.json','noaa-topobathy-subset.tif'):
    shutil.copy2(source/name,destination/name)
c=json.loads((source/'design.json').read_text());c['grid_sizes']=[n]
c['selection']+=' Resolution-only candidate: same center, extent, observations, native terrain, footprints, forcing and physical parameters. No coordinate or water-level fitting.'
(destination/'design.json').write_text(json.dumps(c,indent=2))
cx,cy=Transformer.from_crs(4326,c['crs'],always_xy=True).transform(*c['center']);half=c['extent_m']/2
with rasterio.open(destination/'noaa-topobathy-subset.tif') as src:
    z=np.full((n,n),np.nan,dtype='f4')
    reproject(src.read(1),z,src_transform=src.transform,src_crs=c['terrain_crs'],src_nodata=src.nodata,
        dst_transform=Affine(c['extent_m']/n,0,cx-half,0,-c['extent_m']/n,cy+half),dst_crs=c['crs'],dst_nodata=np.nan,resampling=Resampling.bilinear)
    if not np.isfinite(z).all():raise ValueError('Incomplete terrain')
    np.save(destination/f'topobathy-{n}.npy',np.flipud(z))
(destination/'candidate-hypothesis.json').write_text(json.dumps({'parent': str(source),
    'hypothesis': 'Finer cells may reduce terrain and building representation errors without tuning physical parameters.',
    'change': 'Grid resolution only','acceptance': 'Retain supported observation cohort and prior wet points, do not increase dry misses, pass mass balance, and avoid worse common-point and equal-site RMSE. Test on a separate event; no general accuracy claim from sparse marks.'},indent=2))
print(destination)
