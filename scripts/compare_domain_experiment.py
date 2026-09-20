"""Assess a larger domain only after verifying exact shared-core inputs."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from services.reference.validation_regression import compare_assessments


def verify_core(old_grid,new_grid,old_z,new_z,old_solid,new_solid):
    for key in ('crs','dx_m','dy_m','elevation_origin_m','row_direction','vertical_datum'):
        if old_grid[key]!=new_grid[key]:raise ValueError('Shared grid convention differs: '+key)
    offsets=[(old_grid[f'origin_{axis}_m']-new_grid[f'origin_{axis}_m'])/old_grid[f'd{axis}_m'] for axis in ('x','y')]
    if any(abs(v-round(v))>1e-8 for v in offsets):raise ValueError('Shared cells are not aligned')
    col,row=(round(v) for v in offsets)
    if row<0 or col<0 or row+old_grid['ny']>new_grid['ny'] or col+old_grid['nx']>new_grid['nx']:raise ValueError('Original domain is not contained')
    core=np.s_[row:row+old_grid['ny'],col:col+old_grid['nx']]
    if not np.array_equal(old_z,new_z[core]):raise ValueError('Shared terrain changed')
    if not np.array_equal(old_solid,new_solid[core]):raise ValueError('Shared buildings changed')
    return row,col

def main():
    root=Path(sys.argv[1]);p=json.loads((root/'protocol.json').read_text());parent=Path(p['parent_directory'])
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    if sha(parent/'protocol.json')!=p['parent_protocol_sha256']:raise ValueError('Parent changed')
    for path,expected in p['source_sha256'].items():
        if sha(Path(path))!=expected:raise ValueError('Frozen source changed: '+path)
    q=json.loads((parent/'protocol.json').read_text());old=next(r for r in q['bundles'] if r['grid_cells']==64);new=p['bundles'][0]
    for key in ('center','roughness','max_step_s','duration_s','start_utc','end_utc','rainfall_m','infiltration_m_s','soil_storage_m','boundary_edge'):
        if p[key]!=q[key]:raise ValueError('Non-domain change: '+key)
    if old['levels']!=new['levels']:raise ValueError('Forcing changed')
    inputs=[]
    for run in (old,new):
        folder=Path('data/local/bundles')/run['bundle_id'];g=json.loads((folder/'manifest.json').read_text())['grid']
        inputs.append((g,np.fromfile(folder/'z.bin',dtype='<f4').reshape(g['ny'],g['nx']),np.fromfile(folder/'solid.bin',dtype='u1').reshape(g['ny'],g['nx'])))
    row,col=verify_core(inputs[0][0],inputs[1][0],inputs[0][1],inputs[1][1],inputs[0][2],inputs[1][2])
    a=next(r for r in json.loads((parent/'accuracy.json').read_text())['runs'] if r['grid_cells']==64)
    b=json.loads((root/'accuracy.json').read_text())['runs'][0]
    result=compare_assessments(a,b)
    result.update(experiment='same-cell-size-domain-extension',core_offset_cells=[row,col],core_inputs_bitwise_identical=True,
        baseline_extent_m=q['extent_m'],candidate_extent_m=p['extent_m'],cell_size_m=inputs[0][0]['dx_m'],
        production_enabled=False,decision='passes_this_development_domain_check_only' if result['regression_gate_passed'] else 'fails_this_development_domain_check',
        limitation='Exposed same-cohort diagnostic. Enlarged exterior geometry and initial connected water change together; a result does not isolate all individual boundary mechanisms or validate general flood accuracy.')
    (root/'domain-comparison.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
