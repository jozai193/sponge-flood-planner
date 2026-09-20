"""Bounded raster windows; retain missing pixels and never interpolate class IDs."""
import hashlib
from datetime import UTC, datetime

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window


def grid_coordinates(manifest):
    g=manifest['grid']
    y,x=np.mgrid[:g['ny'],:g['nx']]
    return Transformer.from_crs(g['crs'],4326,always_xy=True).transform(
        g['origin_x_m']+(x+.5)*g['dx_m'],g['origin_y_m']+(y+.5)*g['dy_m'])


def bounds_for(manifest):
    g=manifest['grid']
    # Densify edges to account for projection curvature; do not bound cell centres.
    t=Transformer.from_crs(g['crs'],4326,always_xy=True)
    return t.transform_bounds(g['origin_x_m'],g['origin_y_m'],
        g['origin_x_m']+g['nx']*g['dx_m'],g['origin_y_m']+g['ny']*g['dy_m'],densify_pts=21)


def sample_window(uri, lon, lat, *, band=1):
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_HTTP_TIMEOUT='25',
                      GDAL_HTTP_MAX_RETRY='1',VSI_CACHE=True), rasterio.open(uri) as src:
        if not src.crs: raise ValueError('Raster CRS is missing')
        x,y=Transformer.from_crs(4326,src.crs,always_xy=True).transform(lon,lat)
        rows,cols=rasterio.transform.rowcol(src.transform,np.asarray(x).ravel(),np.asarray(y).ravel())
        rows,cols=np.asarray(rows).reshape(lon.shape),np.asarray(cols).reshape(lon.shape)
        inside=(rows>=0)&(rows<src.height)&(cols>=0)&(cols<src.width)
        out=np.full(lon.shape,np.nan)
        if inside.any():
            r0,r1=int(rows[inside].min()),int(rows[inside].max())+1
            c0,c1=int(cols[inside].min()),int(cols[inside].max())+1
            if (r1-r0)*(c1-c0)>4_000_000:raise ValueError('Raster window exceeds pixel budget')
            data=src.read(band,window=Window(c0,r0,c1-c0,r1-r0),masked=True).astype(float).filled(np.nan)
            out[inside]=data[rows[inside]-r0,cols[inside]-c0]*src.scales[band-1]+src.offsets[band-1]
        source={'source_url': str(uri),'horizontal_crs': src.crs.to_string(),
            'native_pixel_size': list(src.res),'sample_method': 'nearest native pixel',
            'band_scale': src.scales[band-1],'band_offset': src.offsets[band-1],'band_units': src.units[band-1],
            'retrieved_at': datetime.now(UTC).isoformat(),
            'sample_sha256': hashlib.sha256(out.astype('<f4').tobytes()).hexdigest()}
        return out,source


def raster_payload(values, sources, **metadata):
    valid=np.isfinite(values)
    return dict(shape=list(values.shape),values=np.where(valid,values,0).ravel().tolist(),
                valid_mask=valid.astype('u1').ravel().tolist(),coverage_fraction=float(valid.mean()),
                sources=sources,**metadata)
