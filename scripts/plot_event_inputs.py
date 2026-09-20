"""Plot terrain, represented buildings and prescribed boundary before scoring."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path(sys.argv[1]);p=json.loads((root/'protocol.json').read_text());run=p['bundles'][-1]
folder=Path('data/local/bundles')/run['bundle_id'];g=json.loads((folder/'manifest.json').read_text())['grid'];shape=(g['ny'],g['nx'])
z=np.fromfile(folder/'z.bin',dtype='<f4').reshape(shape)+g['elevation_origin_m'];solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(shape)
fig,ax=plt.subplots(figsize=(7,7),constrained_layout=True)
extent=(0,p['extent_m'],0,p['extent_m']);im=ax.imshow(z,origin='lower',extent=extent,cmap='terrain',vmin=-3,vmax=5)
ax.imshow(np.ma.masked_where(solid==0,solid),origin='lower',extent=extent,cmap='Greys',vmin=0,vmax=1,alpha=.8)
edge=p['boundary_edge'];L=p['extent_m'];segments={'west':([0,0],[0,L]),'east':([L,L],[0,L]),'south':([0,L],[0,0]),'north':([0,L],[L,L])}
ax.plot(*segments[edge],lw=5,color='#e4359d',label='Prescribed reservoir edge',clip_on=False)
if (root/'suitability.json').exists():
    samples=json.loads((root/'suitability.json').read_text())[-1]['in_domain']
    for s in samples:
        color='#00ffe0' if s['eligibility']=='outdoor' and not s['solid'] else '#b72b0d'
        x=(s['col']+.5)*g['dx_m'];y=(s['row']+.5)*g['dy_m']
        ax.scatter(x,y,marker='x',s=75,c=color,linewidth=2)
        ax.annotate(str(s['id']),(x,y),xytext=(5,5),textcoords='offset points',fontsize=8)
ax.set(xlabel='East from domain origin (m)',ylabel='North from domain origin (m)',title=p['city']+' · frozen input geometry\nCyan: outdoor non-solid marks; red: unsupported')
fig.colorbar(im,ax=ax,shrink=.7,label='Terrain elevation (m NAVD88)');ax.legend(loc='upper left',fontsize=8)
fig.savefig(root/'input-geometry.png',dpi=130)
print(root/'input-geometry.png')
