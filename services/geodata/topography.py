"""Read-only terrain diagnostics; never fill depressions in the solver bed."""
import heapq

import numpy as np


def terrain_metrics(z,dx,dy,solid=None):
    z=np.asarray(z,dtype=float)
    if z.ndim!=2 or min(z.shape)<2 or not np.isfinite(z).all() or dx<=0 or dy<=0:
        raise ValueError('Expected finite 2D terrain and positive cell spacing')
    ny,nx=z.shape
    blocked=np.zeros(z.shape,dtype=bool) if solid is None else np.asarray(solid,dtype=bool)
    if blocked.shape!=z.shape:raise ValueError('Obstacle shape mismatch')
    # Four-neighbour priority flood matches face-connected surface transport.
    # Domain edges are diagnostic spill exits, not imposed hydraulic outlets.
    seen=blocked.copy();filled=z.copy();queue=[]
    for y in range(ny):
        for x in range(nx):
            if (y in (0,ny-1) or x in (0,nx-1)) and not seen[y,x]:
                seen[y,x]=True;heapq.heappush(queue,(z[y,x],y,x))
    while queue:
        level,y,x=heapq.heappop(queue)
        for yy,xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
            if 0<=yy<ny and 0<=xx<nx and not seen[yy,xx]:
                seen[yy,xx]=True;filled[yy,xx]=max(level,z[yy,xx])
                heapq.heappush(queue,(filled[yy,xx],yy,xx))
    valid=seen&~blocked;depression=np.where(valid,filled-z,0)
    gy,gx=np.gradient(z,dy,dx)
    return {'min_elevation_m': float(z.min()),'max_elevation_m': float(z.max()),'relief_m': float(np.ptp(z)),
        'max_slope_m_per_m': float(np.hypot(gx,gy).max()),
        'depression_area_m2': float(np.count_nonzero(depression>0.01)*dx*dy),
        'depression_storage_m3': float(depression.sum()*dx*dy),
        'deepest_depression_m': float(depression.max()),
        'unresolved_enclosed_area_m2': float(np.count_nonzero(~seen&~blocked)*dx*dy)}
