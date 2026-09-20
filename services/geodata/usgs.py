"""Direct USGS raster window sampling; no OpenTopography entitlement needed."""
from urllib.parse import urlparse

import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds


def sample_products(products, crs, xmin, ymin, n, dx):
    target=np.full((n,n),np.nan,dtype=np.float32)
    sources=[]
    for item in products[:12]:
        url=item.get("downloadURL","")
        host=urlparse(url).hostname or ""
        if not (host.endswith(".usgs.gov") or host in ("prd-tnm.s3.amazonaws.com","prd-tnm.s3.us-west-2.amazonaws.com")):
            continue
        if not url.lower().endswith((".tif",".tiff")):continue
        with rasterio.Env(GDAL_HTTP_TIMEOUT="60",GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                          CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff"), rasterio.open(url) as src:
                if src.crs is None:raise ValueError("USGS raster lacks CRS")
                transformer=Transformer.from_crs(crs,src.crs,always_xy=True)
                bounds=transformer.transform_bounds(xmin,ymin,xmin+n*dx,ymin+n*dx,densify_pts=21)
                window=from_bounds(*bounds,src.transform).round_offsets().round_lengths()
                window=window.intersection(rasterio.windows.Window(0,0,src.width,src.height))
                if window.width*window.height>25_000_000:raise ValueError("Source raster window exceeds memory budget")
                array=src.read(1,window=window)
                out=np.full((n,n),np.nan,dtype=np.float32)
                reproject(array,out,src_transform=src.window_transform(window),src_crs=src.crs,
                          src_nodata=src.nodata,dst_transform=Affine(dx,0,xmin,0,-dx,ymin+n*dx),
                          dst_crs=crs,dst_nodata=np.nan,resampling=Resampling.bilinear)
                out=np.flipud(out)
                target=np.where(np.isfinite(target),target,out)
                sources.append({"provider":"USGS 3DEP","source_url":url,"title":item.get("title"),
                                "source_id":item.get("sourceId"),"publication_date":item.get("publicationDate"),
                                "native_resolution_m":abs(src.transform.a),"attribution":"USGS 3DEP",
                                "vertical_datum":"Read source metadata before building-loss use"})
        if np.isfinite(target).all():break
    if not np.isfinite(target).all():raise ValueError("USGS assets did not cover complete requested grid")
    return target,sources,"USGS source datum requires metadata confirmation"
