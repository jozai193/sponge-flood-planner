"""Separate terrain and footprint effects on initial coastal connectivity only."""
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

base=Path(sys.argv[1]);candidate=Path(sys.argv[2]);inputs=[]
for folder in (base,candidate):
    p=json.loads((folder/'protocol.json').read_text());run=p['bundles'][-1]
    bundle=Path('data/local/bundles')/run['bundle_id'];g=json.loads((bundle/'manifest.json').read_text())['grid']
    inputs.append({'folder': folder,'p': p,'g': g,
        'z': np.fromfile(bundle/'z.bin',dtype='<f4').reshape(g['ny'],g['nx']).astype(float)+g['elevation_origin_m'],
        'solid': np.fromfile(bundle/'solid.bin',dtype='u1').reshape(g['ny'],g['nx']),
        'level': run['levels'][0]['elevationM']+g['elevation_origin_m']})
a,b=inputs
if b['g']['nx']!=2*a['g']['nx'] or b['g']['ny']!=2*a['g']['ny']:raise ValueError('Requires aligned doubled resolution')
for key in ('origin_x_m','origin_y_m','crs'):
    if a['g'][key]!=b['g'][key]:raise ValueError('Unaligned domains')
if abs(a['level']-b['level'])>1e-9:raise ValueError('Initial gauge differs')
expand=lambda x:np.repeat(np.repeat(x,2,axis=0),2,axis=1)
terrain=[expand(a['z']),b['z']];solids=[expand(a['solid']),b['solid']]
edge=b['p'].get('boundary_edge','west');level=b['level'];ny,nx=b['z'].shape
area=b['g']['dx_m']*b['g']['dy_m'];cases=[]
for iz in (0,1):
    for ib in (0,1):
        z=terrain[iz];solid=solids[ib];seen=np.zeros((ny,nx),bool);queue=deque()
        boundary=[(y,0) for y in range(ny)] if edge=='west' else [(y,nx-1) for y in range(ny)] if edge=='east' else [(0,x) for x in range(nx)] if edge=='south' else [(ny-1,x) for x in range(nx)]
        def visit(y,x,seen=seen,solid=solid,z=z,queue=queue,level=level):
            if 0<=y<ny and 0<=x<nx and not seen[y,x] and not solid[y,x] and z[y,x]<level:
                seen[y,x]=True;queue.append((y,x))
        for y,x in boundary:visit(y,x)
        while queue:
            y,x=queue.popleft()
            for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):visit(y+dy,x+dx)
        depth=np.where(seen,level-z,0)
        row={'terrain': 'fine' if iz else 'coarse','buildings': 'fine' if ib else 'coarse',
            'connected_initial_area_m2': float(seen.sum()*area),'initial_volume_m3': float(depth.sum()*area),
            'below_level_disconnected_area_m2': float(((z<level)&~seen&~solid.astype(bool)).sum()*area),
            'solid_area_m2': float(solid.sum()*area)}
        if iz==ib:
            original=inputs[iz];n=original['g']['nx']
            sim=json.loads((original['folder']/f'simulation-{n}.json').read_text())
            saved=np.array(sim['frames'][0]['depth']).reshape(n,n)
            if not iz:saved=expand(saved)
            row['maximum_depth_difference_from_saved_initialization_m']=float(np.max(np.abs(saved-depth)))
            if not np.allclose(saved,depth,atol=2e-6,rtol=2e-6):raise ValueError('Initialization reconstruction differs')
        cases.append(row)
out={'cases': cases,'initial_gauge_navd88_m': level,
    'method': 'Four-neighbor reservoir connectivity on the aligned fine lattice. Coarse bed and masks are repeated into 2x2 cells. Only terrain and building representation are swapped; no HWM elevations enter this diagnostic.',
    'limitation': 'Mixed terrain/mask cases are diagnostic counterfactuals, not full hydraulic runs or candidate improvements. Initial volume and connectivity changes do not isolate causes of later flood error. Fine geometry is not independent ground truth.'}
(candidate/'initialization-diagnosis.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
