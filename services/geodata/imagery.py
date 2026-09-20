import math

from pyproj import Transformer


def descriptor(manifest):
    grid=manifest['grid'];extent=manifest['extent_m']
    transform=Transformer.from_crs(grid['crs'],3857,always_xy=True)
    corners=[transform.transform(grid['origin_x_m']+x*extent,grid['origin_y_m']+y*extent) for x,y in [(0,0),(1,0),(1,1),(0,1)]]
    zoom=18 if extent<=600 else 17 if extent<=1200 else 16
    n=2**zoom;limit=20037508.342789244
    pixels=[[(x+limit)/(2*limit)*n*256,(limit-y)/(2*limit)*n*256] for x,y in corners]
    x0=math.floor(min(p[0] for p in pixels)/256);x1=math.floor(max(p[0] for p in pixels)/256)
    y0=math.floor(min(p[1] for p in pixels)/256);y1=math.floor(max(p[1] for p in pixels)/256)
    if (x1-x0+1)*(y1-y0+1)>64:raise ValueError('Imagery tile budget exceeded')
    width=(x1-x0+1)*256;height=(y1-y0+1)*256
    return {'width':width,'height':height,'cornersUV':[[(x-x0*256)/width,(y-y0*256)/height] for x,y in pixels],
      'tiles':[{'x':(x-x0)*256,'y':(y-y0)*256,'url':f'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{y}/{x}'} for y in range(y0,y1+1) for x in range(x0,x1+1)]}
