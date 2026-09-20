"""Describe model wetting and peak timing without claiming observed timing skill."""
import json
import sys
from pathlib import Path

import numpy as np

root=Path(sys.argv[1]);p=json.loads((root/'protocol.json').read_text());r=p['bundles'][-1]
a=json.loads((root/'accuracy.json').read_text())['runs'][-1]
sim=json.loads((root/f'simulation-{r["grid_cells"]}.json').read_text());g=sim['grid'];frames=sim['frames']
times=np.array([f['time_s'] for f in frames]);levels=r['levels'];peak_knot=max(levels,key=lambda k:k['elevationM'])
rows=[]
for s in a['samples']:
    i=s['row']*g['nx']+s['col'];h=np.array([f['depth'][i] for f in frames]);running=np.array([f['maxDepth'][i] for f in frames]);wet=np.flatnonzero(h>.01)
    peak=float(running[-1]);attained=np.flatnonzero(running>=peak-1e-6)
    first=int(attained[0]) if peak>.01 and len(attained) else None
    rows.append({'id': s['observation_id'],'status': s['status'],'peak_depth_m': peak,
        'maximum_sampled_depth_m': float(h.max()),'peak_between_snapshot_excess_m': peak-float(h.max()),
        'first_saved_wet_time_s': float(times[wet[0]]) if len(wet) else None,
        'peak_attainment_interval_s': [float(times[max(0,first-1)]),float(times[first])] if first is not None else None,
        'still_wet_at_end': bool(h[-1]>.01),'initially_wet': bool(h[0]>.01)})
out={'gauge_peak_time_s': peak_knot['timeS'],'snapshot_gap_s': float(np.diff(times).max()),'observations': rows,
    'limitation': 'HWM observations provide maxima without arrival times. These model-only intervals diagnose snapshot sampling and incomplete drainage; they do not validate observed flood timing. Running maxima retain peaks between saved depth snapshots.'}
(root/'timing-diagnosis.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
