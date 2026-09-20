"""Show modeled misses inside the published inundation polygon, not an accuracy badge."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import json

import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

root=Path('artifacts/validation/sandy-2012')
audit=json.loads((root/'extent-comparison.json').read_text())
diag=json.loads((root/'connectivity-diagnosis.json').read_text())
colors=['#f3eee2','#74bcb8','#d98d43','#a9453d','#596c9c','#8c938d']
labels=['Outside mapped extent','Model wet inside map','Dry: ground ≥ gauge peak',
        'Dry: below peak, disconnected','Dry: connected path','Building cells unresolved']
fig,axes=plt.subplots(1,2,figsize=(12,6.8),constrained_layout=True)
for ax,run in zip(axes,audit['runs']):
    n=run['grid_cells'];folder=Path('data/local/bundles')/run['bundle_id']
    area=np.array(run['cell_reference_area_m2'])
    solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(n,n)
    classification=np.array(next(r for r in diag['runs'] if r['grid_cells']==n)['classification'])
    cats=np.where(area>0,1,0)
    for k in (1,2,3):cats[classification==k]=k+1
    cats[(solid>0)&(area>0)]=5
    ax.imshow(cats,origin='lower',extent=[0,1000,0,1000],cmap=ListedColormap(colors),norm=BoundaryNorm(np.arange(7)-.5,6),interpolation='nearest')
    ax.set(xlabel='Easting within domain (m)',ylabel='Northing within domain (m)',
        title=f'{n} × {n} cells\nMapped area modeled dry: {run["predicted_dry_mapped_area_m2"]:,.0f} m²')
fig.suptitle('Sandy 2012: where the simulation misses the published flood zone',fontsize=16)
fig.legend(handles=[Patch(facecolor=c,label=l) for c,l in zip(colors,labels)],
    loc='outside lower center',ncol=3,fontsize=9,frameon=False)
fig.savefig(root/'extent-diagnosis.png',dpi=150)
print((root/'extent-diagnosis.png').resolve())
