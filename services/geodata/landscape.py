"""Global display context from classified cover, never hydraulic geometry."""
import math
from functools import lru_cache

import numpy as np
from shapely.geometry import LineString, Point, shape
from shapely.ops import unary_union

from services.geodata.global_sources import tiled_raster


@lru_cache(maxsize=16)
def cover_grid(crs, x, y, extent):
    n=min(256, max(1, math.ceil(extent/10)))
    grid={'crs': crs, 'origin_x_m': x, 'origin_y_m': y, 'nx': n, 'ny': n,
              'dx_m': extent/n, 'dy_m': extent/n}
    return tiled_raster({'grid': grid, 'extent_m': extent}, 'landcover')


def add_landscape(manifest, context):
    grid=manifest['grid']; extent=manifest['extent_m']
    raster=cover_grid(grid['crs'],grid['origin_x_m'],grid['origin_y_m'],extent)
    ny,nx=raster['shape']; dx=extent/nx; dy=extent/ny
    values=np.asarray(raster['values']).reshape(ny,nx)
    valid=np.asarray(raster['valid_mask'],dtype=bool).reshape(ny,nx)
    exclusions=[shape(b['geometry']).buffer(3) for b in manifest.get('buildings',[])]
    exclusions += [LineString(r['path']).buffer(3) for r in context['roads'] if len(r['path'])>1]
    exclusions += [Point(t['position']).buffer(7) for t in context['trees']]
    excluded=unary_union(exclusions)
    water=[]
    tree_stride=max(1,math.ceil(int(np.count_nonzero(valid & np.isin(values,[10,95])))/8000))
    tree_index=0
    for row,col in zip(*np.where(valid)):
        x=-extent/2+col*dx; y=-extent/2+row*dy
        if values[row,col] in (10,95):
            tree_index+=1
            if tree_index % tree_stride:continue
            # Stable jitter avoids a plantation grid; these are NOT surveyed trees.
            seed=(int(row)*73856093) ^ (int(col)*19349663)
            px=x+dx*(.25+(seed%101)/200); py=y+dy*(.25+((seed//101)%101)/200)
            if not excluded.covers(Point(px,py)):
                context['trees'].append({'id': f'cover-{row}-{col}','position': [px,py],
                    'basis': 'classified-cover'})
        elif values[row,col]==80:
            water.append({'id': f'cover-water-{row}-{col}',
                'name': 'Mapped permanent water · display only, not simulated flood depth',
                'polygon': [[x,y],[x+dx,y],[x+dx,y+dy],[x,y+dy],[x,y]]})
    context['water']=water
    context['landscape_sources']=raster['sources']
    context['assumptions'].append('ESA WorldCover 2021, 10 m, CC BY 4.0: illustrative trees within classified tree cover; positions and dimensions are not surveyed. Classification can be outdated or wrong. Permanent water includes inland and coastal water; no ocean is inferred from missing pixels or low terrain. Water is draped display context, not bathymetry, sea level or tsunami forcing.')
    context['landscape_status']=f"WorldCover 2021 coverage: {raster['coverage_fraction']:.0%}"
    return context
