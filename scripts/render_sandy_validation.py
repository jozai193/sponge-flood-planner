"""Produce a local scientific inspection page from completed measured-event runs."""
import json
from pathlib import Path

import numpy as np

root=Path('artifacts/validation/sandy-2012')
audit=json.loads((root/'accuracy.json').read_text())
protocol=json.loads((root/'protocol.json').read_text())
protocol['limitations']=audit['limitations']
runs=[]
for result in audit['runs']:
    n=result['grid_cells'];s=json.loads((root/f'simulation-{n}.json').read_text())
    folder=Path('data/local/bundles')/result['bundle_id']
    runs.append({'n':n,'solid':np.fromfile(folder/'solid.bin',dtype='u1').tolist(),
        'times':[f['time_s'] for f in s['frames']],
        'depths':[[round(h,4) for h in f['depth']] for f in s['frames']],
        'peak':[round(h,4) for h in s['frames'][-1]['maxDepth']],
        'result':result})
data=json.dumps({'runs':runs,'protocol':protocol},separators=(',',':')).replace('<','\\u003c')
template=Path('scripts/sandy_validation_view.html').read_text(encoding='utf-8')
(root/'inspection.html').write_text(template.replace('/*VALIDATION_DATA*/',data),encoding='utf-8')
print((root/'inspection.html').resolve())
