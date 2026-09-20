"""Classify mapped dry cells against a static connectivity diagnostic, without fitting."""
import json
from collections import deque
from pathlib import Path

import numpy as np

root=Path('artifacts/validation/sandy-2012')
protocol=json.loads((root/'protocol.json').read_text())
extent=json.loads((root/'extent-comparison.json').read_text())
results=[]
for run in protocol['bundles']:
    n=run['grid_cells'];folder=Path('data/local/bundles')/run['bundle_id']
    grid=json.loads((folder/'manifest.json').read_text())['grid']
    bed=np.fromfile(folder/'z.bin',dtype='<f4').reshape(n,n)
    solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(n,n).astype(bool)
    sim=json.loads((root/f'simulation-{n}.json').read_text())
    peak=np.array(sim['frames'][-1]['maxDepth']).reshape(n,n)
    area=np.array(next(r for r in extent['runs'] if r['grid_cells']==n)['cell_reference_area_m2'])
    level=max(k['elevationM'] for k in run['levels'])
    eligible=(bed<level)&~solid
    reached=np.zeros((n,n),dtype=bool);queue=deque()
    for row in range(n):
        if eligible[row,0]:reached[row,0]=True;queue.append((row,0))
    while queue:
        row,col=queue.popleft()
        for rr,cc in ((row-1,col),(row+1,col),(row,col-1),(row,col+1)):
            if 0<=rr<n and 0<=cc<n and eligible[rr,cc] and not reached[rr,cc]:
                reached[rr,cc]=True;queue.append((rr,cc))
    dry=(peak<=.01)&~solid&(area>0)
    classes={'ground_at_or_above_gauge_peak':dry&(bed>=level),
             'below_peak_but_disconnected':dry&(bed<level)&~reached,
             'below_peak_and_connected':dry&reached}
    masks=np.zeros((n,n),dtype='u1')
    for i,(name,mask) in enumerate(classes.items(),1):masks[mask]=i
    result={'grid_cells': n,'classes': {name:{'cells': int(mask.sum()),'mapped_area_m2': float(area[mask].sum())} for name,mask in classes.items()},'classification': masks.tolist()}
    results.append(result);print(n,result['classes'])
(root/'connectivity-diagnosis.json').write_text(json.dumps({'runs': results,
    'method': 'Four-neighbor paths from existing west reservoir using fixed bed, solids and supplied gauge peak. Diagnostic only: assumes a constant peak held indefinitely, omits momentum and dynamic overtopping, and does not predict event depths.',
    'interpretation': 'Above-peak cells point to terrain/map/boundary-level discrepancies. Disconnected cells point to represented barriers. Connected dry cells require duration, routing and wetting-threshold investigation. These categories are hypotheses, not verified causal attribution.'},indent=2))
