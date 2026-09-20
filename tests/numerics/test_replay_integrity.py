from copy import deepcopy

import numpy as np
import pytest

from services.reference.replay_integrity import validate_replay


def frames():
    ledger={'initial_m3': 1,'rain_m3': 0,'inflow_m3': 0,'stored_m3': 1,'outflow_m3': 0,
                'deep_percolation_m3': 0,'residual_m3': 0,'relative_residual': 0}
    return [{'time_s': t,'depth': [h],'maxDepth': [.5],'ledger': deepcopy(ledger)} for t,h in [(0,.5),(1,.4),(2,.3)]]


def check(f):return validate_replay(f,(1,1),np.zeros((1,1)),2,expected_frames=3)


def test_saved_replay_passes_and_rejects_hidden_intermediate_corruption():
    assert check(frames())['mass_gate_passed']
    for field,value,message in [('depth',[float('nan')],'Nonfinite'),('maxDepth',[.2],'Peak history'),('time_s',0,'timestamps')]:
        f=frames();f[1][field]=value
        with pytest.raises(ValueError,match=message):check(f)
    f=frames();f[-1]['maxDepth']=[.4]
    with pytest.raises(ValueError,match='decreases'):check(f)


def test_ledger_cannot_hide_mass_error_by_claiming_zero_residual():
    f=frames();f[1]['ledger']['stored_m3']=.9
    with pytest.raises(ValueError,match='signed water ledger'):check(f)
    f[1]['ledger']['residual_m3']=.1
    with pytest.raises(ValueError,match='relative water ledger'):check(f)
    f[1]['ledger']['relative_residual']=.1
    assert not check(f)['mass_gate_passed']


def test_self_consistent_ledger_must_match_actual_saved_depths():
    f=frames()
    for frame in f:
        frame['ledger'].update(surface_m3=frame['depth'][0],subsurface_m3=1-frame['depth'][0])
    def volume_check():return validate_replay(f,(1,1),np.zeros((1,1)),2,expected_frames=3,cell_area_m2=1)
    assert volume_check()['depth_volume_crosscheck_passed']
    f[1]['depth']=[.2]
    with pytest.raises(ValueError,match='depths disagree'):volume_check()
    f[1]['depth']=[.4];f[1]['ledger']['subsurface_m3']=.5
    with pytest.raises(ValueError,match='partition inconsistent'):volume_check()
