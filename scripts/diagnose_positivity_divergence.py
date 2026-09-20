"""Describe the frozen candidate gate failure without changing its threshold."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path('artifacts/validation/sandy-2012-positivity-v1')
parent=Path('artifacts/validation/sandy-2012-grid128')
paths=[parent/'simulation-128.json',root/'simulation-128.json',root/'candidate-comparison.json']
a,b,gate=[json.loads(p.read_text()) for p in paths];rows=[]
for index,(original,candidate) in enumerate(zip(a['frames'],b['frames'])):
    delta=np.abs(np.asarray(original['depth'])-np.asarray(candidate['depth']));i=int(np.argmax(delta))
    peak=np.abs(np.asarray(original['maxDepth'])-np.asarray(candidate['maxDepth']))
    rows.append({'frame': index,'time_s': original['time_s'],'max_depth_difference_m': float(delta[i]),
        'max_peak_difference_m': float(peak.max()),'cell_index': i,'row': i//128,'column': i%128,
        'original_depth_m': original['depth'][i],'candidate_depth_m': candidate['depth'][i],
        'cumulative_correction_m3': candidate['ledger']['roundoff_correction_m3']})
out={'original_steps': a['steps'],'candidate_steps': b['steps'],
    'first_saved_difference': next((r for r in rows if r['max_depth_difference_m']>0),None),
    'first_saved_correction': next((r for r in rows if r['cumulative_correction_m3']>0),None),
    'largest_saved_difference': max(rows,key=lambda r:r['max_depth_difference_m']),
    'frames_exceeding_frozen_depth_gate': [r for r in rows if r['max_depth_difference_m']>1e-4],
    'frozen_gate_passed': gate['candidate_numerical_regression_passed'],
    'source_sha256': {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
    'limitation': 'Saved-frame localization only; the exact intervening arithmetic is not observed. The engineering threshold is retained. Numerical agreement is not evidence of real-world accuracy.'}
(root/'divergence-diagnosis.json').write_text(json.dumps(out,indent=2))
fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True,constrained_layout=True)
hours=[r['time_s']/3600 for r in rows]
axes[0].plot(hours,[r['max_depth_difference_m']*1000 for r in rows],label='Largest depth difference',color='#087c91')
axes[0].plot(hours,[r['max_peak_difference_m']*1000 for r in rows],label='Largest running-peak difference',color='#bb4b27')
axes[0].axhline(.1,color='#742550',ls='--',label='Frozen 0.1 mm limit')
axes[0].set(ylabel='Difference (mm)',title='Sandy: strict replay now passes, but frozen change gate fails')
axes[0].legend();axes[0].grid(alpha=.2)
axes[1].step(hours,[r['cumulative_correction_m3']*1e9 for r in rows],where='post',color='#087c91')
axes[1].set(xlabel='Simulated hours',ylabel='Cumulative correction (10⁻⁹ m³)',xlim=(0,18))
axes[1].grid(alpha=.2)
fig.suptitle('Original output preserved; same terrain, forcing, grid and 587,611 timesteps\nOnly one saved frame exceeds the depth gate. This does not establish or disprove practical flood accuracy.',fontsize=11)
fig.savefig(root/'divergence-diagnosis.png',dpi=145)
print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'},indent=2))
