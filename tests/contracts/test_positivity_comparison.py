import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize('tiny_negative,peak_change,expected',[(False,0.,True),(True,0.,True),(False,.001,False)])
def test_candidate_comparison_retains_original_failure_and_peak_gate(tmp_path,tiny_negative,peak_change,expected):
    repo=Path(__file__).resolve().parents[2]
    base=tmp_path/'base';candidate=tmp_path/'candidate';base.mkdir();candidate.mkdir()
    (base/'protocol.json').write_text('{}')
    digest=hashlib.sha256((base/'protocol.json').read_bytes()).hexdigest()
    (candidate/'protocol.json').write_text(json.dumps({'candidate_parent_directory': str(base),'candidate_parent_protocol_sha256': digest,'bundles': [{'grid_cells': 2}],'duration_s': 120}))
    (candidate/'evaluation-plan.json').write_text('{}')
    folder=tmp_path/'data/local/bundles/synthetic';folder.mkdir(parents=True);(folder/'solid.bin').write_bytes(bytes(2))
    ledger={'initial_m3': 1.,'rain_m3': 0.,'inflow_m3': 0.,'stored_m3': 1.,'surface_m3': 1.,'subsurface_m3': 0.,'outflow_m3': 0.,'deep_percolation_m3': 0.,'residual_m3': 0.,'relative_residual': 0.}
    original={'bundle_id': 'synthetic','inputHash': 'same','grid': {'nx': 2,'ny': 1,'dx_m': 1.,'dy_m': 1.},'frames': [{'time_s': i,'depth': [1.,0.],'maxDepth': [1.,0.],'ledger': copy.deepcopy(ledger)} for i in range(121)]}
    result=copy.deepcopy(original)
    if tiny_negative:original['frames'][-1]['depth'][1]=-5e-12
    for f in result['frames']:
        f['ledger'].update(roundoff_correction_m3=0.,roundoff_adjusted_residual_m3=0.)
        f['maxDepth'][0]+=peak_change
    for folder,sim in ((base,original),(candidate,result)):(folder/'simulation-2.json').write_text(json.dumps(sim))
    subprocess.run([sys.executable,str(repo/'scripts/compare_positivity_replay.py'),str(candidate)],cwd=tmp_path,env={**os.environ,'PYTHONPATH':str(repo)},check=True,capture_output=True)
    compared=json.loads((candidate/'candidate-comparison.json').read_text())
    assert compared['candidate_numerical_regression_passed'] is expected
    assert compared['original_integrity']['replay_structure_passed'] is (not tiny_negative)
    assert compared['production_enabled'] is False
