import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

from scripts.diagnose_replay_failure import diagnose


def fixture():
    ledger = {'initial_m3': 1., 'rain_m3': 0., 'inflow_m3': 0., 'stored_m3': 1.,
        'surface_m3': 1., 'subsurface_m3': 0., 'outflow_m3': 0., 'deep_percolation_m3': 0.,
        'residual_m3': 0., 'relative_residual': 0.}
    return {'bundle_id': 'synthetic', 'grid': {'nx': 2,'ny': 1,'dx_m': 1.,'dy_m': 1.},
        'frames': [{'time_s': i, 'depth': [1.,0.], 'maxDepth': [1.,0.], 'ledger': copy.deepcopy(ledger)} for i in range(121)]}


def test_roundoff_sensitivity_never_changes_raw_acceptance_or_input():
    sim=fixture(); sim['frames'][119]['depth'][1]=-5e-12
    before=copy.deepcopy(sim)
    result=diagnose(sim,np.zeros((1,2),dtype='u1'),120)
    assert not result['accepted_for_accuracy']
    assert result['invalid_values'][0]['cell_index']==1
    assert result['diagnostic_only_zeroing_submicrometre_negatives']['replay_structure_passed']
    assert sim==before


def test_sensitivity_preserves_material_negatives_and_other_ledger_failures():
    sim=fixture(); sim['frames'][119]['depth'][1]=-.1
    assert not diagnose(sim,np.zeros((1,2),dtype='u1'),120)['diagnostic_only_zeroing_submicrometre_negatives']['replay_structure_passed']
    sim['frames'][119]['depth'][1]=-5e-12
    sim['frames'][100]['depth'][0]=.8
    result=diagnose(sim,np.zeros((1,2),dtype='u1'),120)
    assert 'surface water ledger' in result['diagnostic_only_zeroing_submicrometre_negatives']['error']
    assert not result['accepted_for_accuracy']


def test_inventory_records_failure_and_continues_to_other_runs(tmp_path):
    repo=Path(__file__).resolve().parents[2]
    bundle=tmp_path/'data/local/bundles/synthetic'; bundle.mkdir(parents=True)
    (bundle/'solid.bin').write_bytes(bytes(2))
    event=tmp_path/'artifacts/validation/sandy-2012'; event.mkdir(parents=True)
    (event/'protocol.json').write_text(json.dumps({'duration_s': 120}))
    valid=fixture(); invalid=copy.deepcopy(valid); invalid['frames'][118]['depth'][1]=-5e-12
    (event/'simulation-32.json').write_text(json.dumps(invalid))
    (event/'simulation-64.json').write_text(json.dumps(valid))
    env={**os.environ,'PYTHONPATH':str(repo)}
    command=[sys.executable,str(repo/'scripts/audit_saved_replays.py')]
    subprocess.run(command,cwd=tmp_path,env=env,check=True,capture_output=True)
    records=json.loads((event.parent/'replay-integrity-audit.json').read_text())
    assert len(records)==2
    assert sum(r['replay_structure_passed'] for r in records)==1
    assert next(r for r in records if not r['replay_structure_passed'])['mass_gate_passed'] is None
    assert subprocess.run(command+['--require-all-valid'],cwd=tmp_path,env=env,capture_output=True,check=False).returncode==1
