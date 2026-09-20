"""Render a portable inspection page; displayed water includes an explicit initial-water mask."""
import json
import sys
from pathlib import Path

import numpy as np

root=Path(sys.argv[1]);audit=json.loads((root/'accuracy.json').read_text())
protocol=json.loads((root/'protocol.json').read_text())
protocol['limitations']=audit.get('limitations',protocol['limitations'])
site_path=root/'site-balanced-assessment.json'
site_data=json.loads(site_path.read_text()) if site_path.exists() else None
runs=[]
for result in audit['runs']:
    if site_data:result['site_balanced_metrics']=next(r for r in site_data['runs'] if r['grid_cells']==result['grid_cells'])['site_balanced']
    n=result['grid_cells'];sim=json.loads((root/f'simulation-{n}.json').read_text())
    folder=Path('data/local/bundles')/result['bundle_id']
    runs.append({'n': n,'solid': np.fromfile(folder/'solid.bin',dtype='u1').tolist(),
        'initial': sim['frames'][0]['depth'],'times': [f['time_s'] for f in sim['frames']],
        'depths': [[round(h,4) for h in f['depth']] for f in sim['frames']],
        'peak': [round(h,4) for h in sim['frames'][-1]['maxDepth']],'result': result})
extent_path=root/'extent-comparison.json'
extent=json.loads(extent_path.read_text()) if extent_path.exists() else None
data=json.dumps({'protocol': protocol,'runs': runs,'extent': extent,
    'input_figure': (root/'input-geometry.png').exists(),
    'forcing_figure': (root/'forcing-and-errors.png').exists()},separators=(',',':')).replace('<','\\u003c')
template=Path('scripts/historical_validation_view.html').read_text(encoding='utf-8')
(root/'inspection.html').write_text(template.replace('/*DATA*/',data),encoding='utf-8')
print((root/'inspection.html').resolve())
