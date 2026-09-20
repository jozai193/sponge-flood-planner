"""Compare two completed grids on a shared depth scale, preserving all marks."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from pyproj import Transformer

base=Path(sys.argv[1]);candidate=Path(sys.argv[2])
fig,axes=plt.subplots(1,2,figsize=(12,6),constrained_layout=True)
for index,(ax,folder) in enumerate(zip(axes,(base,candidate))):
    p=json.loads((folder/'protocol.json').read_text());runs=json.loads((folder/'accuracy.json').read_text())['runs']
    r=next(r for r in runs if r['grid_cells']==int(sys.argv[3+index])) if len(sys.argv)>4 else runs[-1]
    sim=json.loads((folder/f'simulation-{r["grid_cells"]}.json').read_text());g=sim['grid'];shape=(g['ny'],g['nx'])
    solid=np.fromfile(Path('data/local/bundles')/r['bundle_id']/'solid.bin',dtype='u1').reshape(shape)
    initial=np.array(sim['frames'][0]['depth']).reshape(shape);peak=np.array(sim['frames'][-1]['maxDepth']).reshape(shape)
    extent=(0,p['extent_m'],0,p['extent_m'])
    background=np.zeros(shape);background[initial>.01]=1;background[solid==1]=2
    ax.imshow(background,origin='lower',extent=extent,cmap=ListedColormap(['#e8dec5','#607c8b','#898f89']),vmin=0,vmax=2)
    plotted=np.ma.masked_where((initial>.01)|(peak<=.01)|(solid==1),peak)
    image=ax.imshow(plotted,origin='lower',extent=extent,cmap='Blues',vmin=0,vmax=1.5)
    # Crosses stay at surveyed coordinates, not cell centres. Co-located
    # observations share one cross but retain every ID in the label.
    geo=json.loads((folder/f'observations-{r["grid_cells"]}.geojson').read_text())
    crs=geo.get('crs',{}).get('properties',{}).get('name','EPSG:4326')
    transform=Transformer.from_crs(crs,g['crs'],always_xy=True)
    positions={f['properties']['id']:transform.transform(*f['geometry']['coordinates']) for f in geo['features']}
    groups={}
    for s in r['samples']:
        px,py=positions[s['observation_id']];key=(round(px-g['origin_x_m'],4),round(py-g['origin_y_m'],4))
        groups.setdefault(key,[]).append(s)
    labels=[]
    for (x,y),samples in sorted(groups.items(),key=lambda entry:entry[0][1]):
        s=samples[0]
        color='#167139' if s['status']=='compared' else '#d46213' if s['status']=='observed_flood_model_dry' else '#963e9f'
        ax.scatter(x,y,c=color,marker='x',s=55,linewidths=2)
        label_y=y+p['extent_m']*.025
        while any(abs(x-lx)<p['extent_m']*.16 and abs(label_y-ly)<p['extent_m']*.045 for lx,ly in labels):label_y+=p['extent_m']*.045
        labels.append((x,label_y))
        ax.annotate(', '.join(str(s['observation_id']) for s in samples),(x,y),xytext=(x+p['extent_m']*.014,label_y),fontsize=7,
            arrowprops={'arrowstyle': '-','color': '#354e52','lw': .5})
    ax.set(title=f'{r["grid_cells"]} × {r["grid_cells"]}: {r["compared_count"]}/{r["total_count"]} compared; {r["missed_flood_count"]} dry misses',xlabel='East (m)',ylabel='North (m)')
fig.colorbar(image,ax=list(axes),shrink=.75,label='Peak depth on initially dry cells (m; capped at 1.5)')
fig.suptitle(p['city']+' · resolution-only comparison\nSlate: initial water; grey: buildings; crosses: green compared, orange dry, purple unresolved',fontsize=12)
fig.savefig(candidate/'grid-comparison.png',dpi=140)
print(candidate/'grid-comparison.png')
