"""Retrieve a small native-resolution NOAA coastal DEM subset, including seabed."""
import json
from pathlib import Path

import httpx
import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.warp import Resampling, reproject

root=Path('artifacts/validation/michael-2018')
base='https://www.ngdc.noaa.gov/thredds/'
dataset='regional/panama_city_13_navd88_2010.nc'
cx,cy=Transformer.from_crs(4326,32616,always_xy=True).transform(-85.654,30.15)
bounds=Transformer.from_crs(32616,4269,always_xy=True).transform_bounds(cx-1100,cy-1100,cx+1100,cy+1100,densify_pts=21)
params={'service': 'WCS','version': '1.0.0','request': 'GetCoverage','coverage': 'Band1',
    'format': 'GeoTIFF_Float','crs': 'OGC:CRS84','bbox': ','.join(map(str,bounds))}
with httpx.Client(timeout=90,follow_redirects=True) as client:
    metadata=client.get(base+'dodsC/'+dataset+'.das');metadata.raise_for_status()
    if 'NAD83' not in metadata.text or 'meters' not in metadata.text:
        raise ValueError('Unexpected source metadata')
    (root/'noaa-topobathy.das').write_text(metadata.text)
    with client.stream('GET',base+'wcs/'+dataset,params=params) as response:
        response.raise_for_status(); chunks=[];total=0
        for chunk in response.iter_bytes():
            total+=len(chunk)
            if total>20_000_000:raise ValueError('Subset exceeds 20 MB budget')
            chunks.append(chunk)
        content=b''.join(chunks)
        request_url=str(response.url)
    (root/'noaa-topobathy-subset.tif').write_bytes(content)
with rasterio.open(root/'noaa-topobathy-subset.tif') as src:
    out=np.full((64,64),np.nan,dtype='f4')
    # THREDDS exports geographic grid coordinates; original dataset explicitly
    # declares NAD83. Preserve that source datum even if service tags EPSG:4326.
    reproject(src.read(1),out,src_transform=src.transform,src_crs='EPSG:4269',
        src_nodata=src.nodata,dst_transform=Affine(2000/64,0,cx-1000,0,-2000/64,cy+1000),
        dst_crs='EPSG:32616',dst_nodata=np.nan,resampling=Resampling.bilinear)
    if not np.isfinite(out).all() or np.any(out<-1000):raise ValueError('Invalid or incomplete coastal DEM')
    np.save(root/'topobathy-64.npy',np.flipud(out))
    description={'request_url': request_url,'source_dataset': dataset,'vertical_datum': 'NAVD88',
        'horizontal_crs': 'EPSG:4269','service_crs': str(src.crs),'shape': src.shape,
        'transform': list(src.transform),'range_m': [float(out.min()),float(out.max())],
        'subset_bytes': len(content),'source_time_range': '1935-2010','publication_year': 2010,
        'metadata_url': 'https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ngdc.mgg.dem:684',
        'limitation': 'Integrated historical topobathymetry approximately 10 m native spacing; old surveys and interpolation can be inaccurate. Not event-era surveyed terrain or a validated hydraulic model.'}
(root/'topobathy-source.json').write_text(json.dumps(description,indent=2))
print(json.dumps(description),flush=True)
