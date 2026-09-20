import json
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds

root=Path('artifacts/validation/michael-2018')
cx,cy=Transformer.from_crs(4326,32616,always_xy=True).transform(-85.6588,30.1503)
extent,n=2200,64
outcomes=[]
for year in ('2017','2020'):
    target=np.full((n,n),np.nan,dtype='f4')
    for p in json.loads((root/'terrain-preflight.json').read_text())['items']:
        if year not in p['title']: continue
        with rasterio.Env(GDAL_HTTP_TIMEOUT='60',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'), \
                rasterio.open(p['downloadURL']) as src:
                b=Transformer.from_crs(32616,src.crs,always_xy=True).transform_bounds(cx-1100,cy-1100,cx+1100,cy+1100)
                w=from_bounds(*b,src.transform).round_offsets().round_lengths().intersection(rasterio.windows.Window(0,0,src.width,src.height))
                a=src.read(1,window=w)
                out=np.full((n,n),np.nan,dtype='f4')
                reproject(a,out,src_transform=src.window_transform(w),src_crs=src.crs,src_nodata=src.nodata,
                    dst_transform=Affine(extent/n,0,cx-1100,0,-extent/n,cy+1100),dst_crs='EPSG:32616',dst_nodata=np.nan,resampling=Resampling.bilinear)
                target=np.where(np.isfinite(target),target,np.flipud(out))
    np.save(root/f'terrain-coverage-{year}.npy',target)
    missing=np.argwhere(~np.isfinite(target))
    inv=Transformer.from_crs(32616,4326,always_xy=True)
    points=[inv.transform(cx-1100+(col+.5)*extent/n,cy-1100+(row+.5)*extent/n) for row,col in missing]
    outcomes.append({'year': year,'missing_cells': len(missing),'total_cells': n*n,'missing_lonlat': points})
    print(year,'missing',len(missing),'range',float(np.nanmin(target)),float(np.nanmax(target)),flush=True)
(root/'terrain-coverage.json').write_text(json.dumps(outcomes,indent=2))
