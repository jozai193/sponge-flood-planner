"""Fetch a bounded, declared-datum NOAA WCS terrain subset for a frozen design."""
import json
import sys
from pathlib import Path

import httpx
import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.warp import Resampling, reproject

root=Path(sys.argv[1]);c=json.loads((root/'design.json').read_text())
if (root/'protocol.json').exists():raise ValueError('Cannot replace frozen terrain')
cx,cy=Transformer.from_crs(4326,c['crs'],always_xy=True).transform(*c['center'])
half=c['extent_m']/2;pad=half+100
bounds=Transformer.from_crs(c['crs'],c['terrain_crs'],always_xy=True).transform_bounds(cx-pad,cy-pad,cx+pad,cy+pad,densify_pts=21)
params={'service': 'WCS','version': '1.0.0','request': 'GetCoverage','coverage': c.get('terrain_coverage','Band1'),'format': 'GeoTIFF_Float','crs': 'OGC:CRS84','bbox': ','.join(map(str,bounds))}
url='https://www.ngdc.noaa.gov/thredds/wcs/'+c['terrain_dataset']
with httpx.stream('GET',url,params=params,timeout=90,follow_redirects=True) as r:
    r.raise_for_status();chunks=[];size=0
    for chunk in r.iter_bytes():
        size+=len(chunk)
        if size>20_000_000:raise ValueError('Subset exceeds 20 MB')
        chunks.append(chunk)
    request_url=str(r.url)
(root/'noaa-topobathy-subset.tif').write_bytes(b''.join(chunks))
with rasterio.open(root/'noaa-topobathy-subset.tif') as src:
    for n in c['grid_sizes']:
        out=np.full((n,n),np.nan,dtype='f4')
        reproject(src.read(1),out,src_transform=src.transform,src_crs=c['terrain_crs'],src_nodata=src.nodata,
            dst_transform=Affine(c['extent_m']/n,0,cx-half,0,-c['extent_m']/n,cy+half),dst_crs=c['crs'],dst_nodata=np.nan,resampling=Resampling.bilinear)
        if not np.isfinite(out).all() or np.any(out<-1000):raise ValueError('Incomplete or invalid terrain')
        np.save(root/f'topobathy-{n}.npy',np.flipud(out))
    source={'request_url': request_url,'source_dataset': c['terrain_dataset'],'horizontal_crs': c['terrain_crs'],'vertical_datum': 'NAVD88',
        'service_crs': str(src.crs),'native_shape': src.shape,'subset_bytes': size,'terrain_date': c['terrain_date'],
        'method': 'Bilinear resampling of declared original horizontal datum; no bay-gap filling or water-level fitting.'}
(root/'topobathy-source.json').write_text(json.dumps(source,indent=2))
print(json.dumps(source))
