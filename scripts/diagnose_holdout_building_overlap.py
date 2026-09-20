"""Explain a metadata-only coverage regression without exposing HWM elevations."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon as PatchPolygon
from matplotlib.patches import Rectangle
from pyproj import Transformer
from shapely.geometry import Point, box, shape
from shapely.ops import transform

root=Path(sys.argv[1]);mid=int(sys.argv[2]);p=json.loads((root/'protocol.json').read_text())
m=next(m for m in json.loads((root/'metadata-screen.json').read_text())['marks'] if m['id']==mid)
src={2:4269,3:4267,4:4326}[m['horizontal_datum_id']]
x,y=Transformer.from_crs(src,p['horizontal_crs'],always_xy=True).transform(m['lon'],m['lat'])
point=Point(x,y);to_grid=Transformer.from_crs(4326,p['horizontal_crs'],always_xy=True)
features=json.loads((root/'current-buildings.geojson').read_text())['features'];near=[]
for f in features:
    geom=transform(to_grid.transform,shape(f['geometry']))
    if geom.distance(point)<70:near.append((f.get('id',f.get('properties',{}).get('id')),geom))
out={'observation_id': mid,'source_description': m['description'],'point_inside_current_footprint': any(geom.covers(point) for _,geom in near),
    'minimum_distance_to_current_footprint_m': min((geom.distance(point) for _,geom in near),default=None),'grids': [],
    'limitation': 'Current source footprints and survey coordinates are not independently verified event-era geometry. Cell-centre rasterization may mark a cell solid even when its observation lies outside the polygon. No observation relocation, building modification or HWM elevation inspection.'}
fig,axes=plt.subplots(1,2,figsize=(10,5),constrained_layout=True)
for ax,run in zip(axes,p['bundles']):
    b=Path('data/local/bundles')/run['bundle_id'];g=json.loads((b/'manifest.json').read_text())['grid'];dx=g['dx_m'];dy=g['dy_m']
    row=int((y-g['origin_y_m'])//dy);col=int((x-g['origin_x_m'])//dx)
    solids=np.fromfile(b/'solid.bin',dtype='u1').reshape(g['ny'],g['nx']);rx=g['origin_x_m']+col*dx;ry=g['origin_y_m']+row*dy
    cell=box(rx,ry,rx+dx,ry+dy);cx,cy=rx+dx/2,ry+dy/2
    out['grids'].append({'grid_cells': run['grid_cells'],'row': row,'col': col,'solid': bool(solids[row,col]),
        'cell_center_inside_current_footprint': any(geom.covers(Point(cx,cy)) for _,geom in near),
        'footprint_area_fraction_in_observation_cell': sum(geom.intersection(cell).area for _,geom in near)/(dx*dy),
        'observation_to_cell_center_m': point.distance(Point(cx,cy))})
    for rr in range(max(0,row-5),min(g['ny'],row+6)):
        for cc in range(max(0,col-5),min(g['nx'],col+6)):
            ax.add_patch(Rectangle((g['origin_x_m']+cc*dx-x,g['origin_y_m']+rr*dy-y),dx,dy,facecolor='#e3d5b9' if solids[rr,cc] else '#edf2ef',edgecolor='#c4ccc6',lw=.5))
    for _,geom in near:
        for poly in ([geom] if geom.geom_type=='Polygon' else geom.geoms):
            coords=np.array(poly.exterior.coords);ax.add_patch(PatchPolygon(coords-[x,y],fill=False,edgecolor='#166a7a',lw=1.5))
    ax.scatter([0],[0],marker='x',s=80,color='#d72655',label='Unchanged observation')
    ax.scatter([cx-x],[cy-y],marker='+',s=70,color='#20252a',label='Containing cell centre')
    ax.set(xlim=(-55,55),ylim=(-55,55),aspect='equal',xlabel='East from observation (m)',ylabel='North from observation (m)',title=f'{run["grid_cells"]} grid: '+('solid / unresolved' if solids[row,col] else 'non-solid'))
axes[0].legend(fontsize=8);fig.suptitle(f'Mark {mid}: same footprint, different containing-cell classification\nTan cells: solid; teal outlines: current source buildings')
fig.savefig(root/'building-overlap-diagnosis.png',dpi=140)
(root/'building-overlap-diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
