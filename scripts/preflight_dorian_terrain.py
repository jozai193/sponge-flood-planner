"""Metadata-only Dorian domain preflight; never opens measured HWM records."""
import hashlib
import json
from pathlib import Path

import httpx
import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.warp import Resampling, reproject

root=Path('artifacts/validation/dorian-2019')
c=json.loads((root/'candidate-screen.json').read_text());domain=c['domain']
cx,cy=Transformer.from_crs(4326,domain['projected_crs'],always_xy=True).transform(domain['center_lon'],domain['center_lat'])
dataset=c['terrain_candidates'][0];base='https://www.ngdc.noaa.gov/thredds/'
metadata=(root/'terrain-metadata.das').read_text()
if 'NAD83' not in metadata or 'NAVD88' not in metadata or '2018:09:11' not in metadata:raise ValueError('Unexpected declared terrain metadata')
bounds=Transformer.from_crs(domain['projected_crs'],4269,always_xy=True).transform_bounds(cx-1100,cy-1100,cx+1100,cy+1100,densify_pts=21)
params={'service': 'WCS','version': '1.0.0','request': 'GetCoverage','coverage': 'Band1','format': 'GeoTIFF_Float','crs': 'OGC:CRS84','bbox': ','.join(map(str,bounds))}
path=root/'noaa-topobathy-subset.tif';request_url=str(httpx.Request('GET',base+'wcs/'+dataset,params=params).url)
if not path.exists():
    with httpx.Client(timeout=90,follow_redirects=True) as client, \
            client.stream('GET',request_url) as response:
            response.raise_for_status(); chunks=[];size=0
            for chunk in response.iter_bytes():
                size+=len(chunk)
                if size>20_000_000:raise ValueError('Subset exceeds 20 MB')
                chunks.append(chunk)
    path.write_bytes(b''.join(chunks))
grids=[]
with rasterio.open(path) as src:
    for n in (64,128):
        out=np.full((n,n),np.nan,dtype='f4')
        reproject(src.read(1),out,src_transform=src.transform,src_crs='EPSG:4269',src_nodata=src.nodata,
            dst_transform=Affine(2000/n,0,cx-1000,0,-2000/n,cy+1000),dst_crs=domain['projected_crs'],dst_nodata=np.nan,resampling=Resampling.bilinear)
        if not np.isfinite(out).all() or np.any(out<-1000):raise ValueError('Incomplete terrain')
        out=np.flipud(out);np.save(root/f'topobathy-{n}.npy',out)
        edges={key:{'min_m': float(a.min()),'max_m': float(a.max()),'cells_below_navd88_zero': int((a<0).sum()),'cells': n} for key,a in [('west',out[:,0]),('east',out[:,-1]),('south',out[0]),('north',out[-1])]}
        grids.append({'grid': n,'range_m': [float(out.min()),float(out.max())],'edges': edges})
    service_crs=str(src.crs);shape=src.shape
result={'status': 'terrain_available_boundary_review_required','request_url': request_url,'source_dataset': dataset,
    'horizontal_crs': 'EPSG:4269','vertical_datum': 'NAVD88','service_crs': service_crs,'native_shape': shape,
    'source_compilation': '2018-09-11; pre-Dorian compilation, individual acquisition dates unresolved',
    'grids': grids,'subset_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'observation_values_exposed': False,
    'limitation': 'Negative terrain is a boundary screening proxy, not verified open water. A barrier-island domain can connect to water on several edges; do not assume one forced edge and three walls are accurate.'}
(root/'terrain-preflight.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
