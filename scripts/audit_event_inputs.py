"""Audit frozen coastal inputs without inspecting high-water elevations."""
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

root=Path(sys.argv[1]);p=json.loads((root/'protocol.json').read_text())
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
if sha(root/'protocol.json')!=(root/'protocol.sha256').read_text().strip():raise ValueError('Changed protocol')
for path,expected in p['source_sha256'].items():
    if sha(Path(path))!=expected:raise ValueError('Changed source: '+path)
results=[]
forcing=json.loads((root/'forcing-preflight.json').read_text())['data']
valid=[r for r in forcing if r.get('v') not in ('',None) and r.get('q')=='v']
if not valid:raise ValueError('No verified forcing')
max_value=max(float(r['v']) for r in valid)
peak_times=[r['t'] for r in valid if float(r['v'])==max_value]
start=datetime.fromisoformat(p['start_utc']);end=datetime.fromisoformat(p['end_utc'])
inside_peak=any(start<=datetime.strptime(t,'%Y-%m-%d %H:%M').replace(tzinfo=UTC)<=end for t in peak_times)
if not inside_peak:raise ValueError('Simulation window omits downloaded gauge peak')
for run in p['bundles']:
    folder=Path('data/local/bundles')/run['bundle_id'];g=json.loads((folder/'manifest.json').read_text())['grid'];shape=(g['ny'],g['nx'])
    z=np.fromfile(folder/'z.bin',dtype='<f4').reshape(shape);s=np.fromfile(folder/'solid.bin',dtype='u1').reshape(shape)
    edge=p.get('boundary_edge','west')
    bed=z[:,0] if edge=='west' else z[:,-1] if edge=='east' else z[0] if edge=='south' else z[-1]
    mask=s[:,0] if edge=='west' else s[:,-1] if edge=='east' else s[0] if edge=='south' else s[-1]
    levels=np.array([k['elevationM'] for k in run['levels']]);times=np.array([k['timeS'] for k in run['levels']])
    if not np.isfinite(levels).all() or times[0]!=0 or times[-1]!=p['duration_s'] or np.any(np.diff(times)<=0):raise ValueError('Invalid forcing coverage')
    cells=bed[mask==0]
    if not len(cells):raise ValueError('No reservoir cells')
    results.append({'grid_cells': g['nx'],'edge': edge,'reservoir_cells': len(cells),
        'below_initial_level_cells': int((cells<levels[0]).sum()),'below_peak_level_cells': int((cells<levels.max()).sum()),
        'boundary_bed_range_navd88_m': [float(cells.min()+g['elevation_origin_m']),float(cells.max()+g['elevation_origin_m'])],
        'forcing_range_navd88_m': [float(levels.min()+g['elevation_origin_m']),float(levels.max()+g['elevation_origin_m'])],
        'source_hashes_passed': True,'forcing_knots': len(levels),'max_forcing_gap_s': float(np.diff(times).max()),
        'downloaded_record_peak_in_simulation_window': inside_peak,'downloaded_peak_times_utc': peak_times,
        'land_cells_below_peak': int(((z<levels.max())&(s==0)&(z>=levels[0])).sum())})
(root/'input-audit.json').write_text(json.dumps({'runs': results,
    'limitation': 'Static terrain and boundary coverage checks only. Below-level terrain does not establish inundation; no observed flood elevations read.'},indent=2))
print(json.dumps(results,indent=2))
