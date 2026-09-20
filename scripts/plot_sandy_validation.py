"""Render scientific result figures from completed, unmodified solver outputs."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import json

import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

root=Path('artifacts/validation/sandy-2012')
protocol=json.loads((root/'protocol.json').read_text())
accuracy=json.loads((root/'accuracy.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(12,4.5),constrained_layout=True)
series=protocol['bundles'][0]['levels']
m=json.loads((Path('data/local/bundles')/protocol['bundles'][0]['bundle_id']/'manifest.json').read_text())
offset=m['grid']['elevation_origin_m']
axes[0].plot([k['timeS']/3600 for k in series],[k['elevationM']+offset for k in series],color='#126d85')
axes[0].set(xlabel='Hours since 2012-10-29 12:00 UTC',ylabel='Water elevation (m NAVD88)',title='Measured NOAA forcing — The Battery')
axes[0].grid(alpha=.25)
colors=['#207b9e','#be571e']
for run,color in zip(accuracy['runs'],colors):
    samples=[r for r in run['samples'] if r['status']=='compared']
    axes[1].scatter([r['observed_elevation_m'] for r in samples],[r['predicted_elevation_m'] for r in samples],label=f"{run['grid_cells']} × {run['grid_cells']} ({run['cell_size_m']:.2f} m)",color=color,alpha=.8)
    if run is accuracy['runs'][-1]:
        offsets={6369:(-25,14),6370:(-25,-17),6364:(12,12),6367:(12,-20),6368:(10,-30)}
        for r in samples:axes[1].annotate(str(r['observation_id']), (r['observed_elevation_m'],r['predicted_elevation_m']),xytext=offsets.get(r['observation_id'],(5,5)),textcoords='offset points',fontsize=7)
axes[1].plot([2.8,3.7],[2.8,3.7],linestyle='--',color='gray',label='Equal observed and modelled elevation')
axes[1].axhline(accuracy['runs'][-1]['gauge_only_baseline']['peak_navd88_m'],linestyle=':',color='#986936',label='Supplied gauge peak')
axes[1].set_xlim(2.8,3.7);axes[1].set_ylim(2.8,3.7)
axes[1].set(xlabel='USGS observed peak (m NAVD88)',ylabel='Modelled peak (m NAVD88)',title='Comparable wet cells only — exclusions in audit')
axes[1].legend(fontsize=7);axes[1].grid(alpha=.25)
fig.suptitle('Sandy 2012: retrospective screening test, not validated hazard prediction',fontsize=12)
fig.savefig(root/'forcing-and-errors.png',dpi=160)
plt.close(fig)
for run in accuracy['runs']:
    data=json.loads((root/f"simulation-{run['grid_cells']}.json").read_text())
    folder=Path('data/local/bundles')/run['bundle_id'];n=run['grid_cells']
    solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(n,n)
    peak=np.array(data['frames'][-1]['maxDepth']).reshape(n,n)
    fig,ax=plt.subplots(figsize=(7,7),constrained_layout=True)
    water=ax.imshow(np.ma.masked_where((solid!=0)|(peak<=.01),peak),origin='lower',extent=(0,1000,0,1000),cmap='Blues',vmin=0,vmax=3)
    ax.imshow(np.ma.masked_where(solid==0,solid),origin='lower',extent=(0,1000,0,1000),cmap=ListedColormap(['#555555']),vmin=0,vmax=1)
    for r in run['samples']:
        if r['status']=='outside_domain':continue
        color='#cc4c02' if r['status']=='observed_flood_model_dry' else '#8b008b' if r['status']!='compared' else '#1b7837'
        x,y=(r['col']+.5)*run['cell_size_m'],(r['row']+.5)*run['cell_size_m']
        ax.scatter([x],[y],marker='x',s=45,c=color)
        ax.annotate(str(r['observation_id']), (x,y),xytext=(4,4),textcoords='offset points',fontsize=7,color=color)
    ax.set(xlabel='Easting from domain origin (m)',ylabel='Northing from domain origin (m)',title=f"Sandy screening: {n} × {n}, peak depth\nGreen: compared; orange: dry miss; purple: unresolved")
    ax.set_facecolor('#f0eee5')
    fig.colorbar(water,ax=ax,label='Peak depth (m), capped at 3 m for display',shrink=.7)
    fig.text(.04,.01,'Grey = current building cells. West includes hydroflattened river; no surveyed bathymetry.',fontsize=8)
    fig.savefig(root/f'peak-depth-{n}.png',dpi=160)
    plt.close(fig)
print('Saved source forcing, observed/modelled comparison and peak-depth maps')
