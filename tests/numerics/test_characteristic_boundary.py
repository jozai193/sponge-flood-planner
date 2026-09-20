import numpy as np
import pytest

from services.reference.characteristic_boundary import CharacteristicBoundary, G, wave_ghost
from services.reference.solver import Surface
from services.reference.solver_wave_candidate import Solver


@pytest.mark.parametrize('edge',['west','east','south','north'])
def test_rest_and_outgoing_simple_wave_are_transmitted(edge):
    np.testing.assert_allclose(wave_ghost([1,0,0],0,1,1,edge),[1,0,0],atol=1e-15)
    h=1.02;u=2*(np.sqrt(G*h)-np.sqrt(G))
    k=1 if edge in ('west','east') else 2;sign=-1 if edge in ('west','south') else 1
    state=np.zeros(3);state[0]=h;state[k]=sign*h*u
    np.testing.assert_allclose(wave_ghost(state,0,1,1,edge),state,atol=1e-15)


def test_incoming_invariant_and_tangential_velocity_are_preserved():
    ghost=wave_ghost([1,.01,.03],0,1.02,1,'east')
    outgoing=.01+2*np.sqrt(G)
    incoming=2*np.sqrt(G)-4*np.sqrt(G*1.02)
    np.testing.assert_allclose(ghost[1]/ghost[0]+2*np.sqrt(G*ghost[0]),outgoing,atol=1e-14)
    np.testing.assert_allclose(ghost[1]/ghost[0]-2*np.sqrt(G*ghost[0]),incoming,atol=1e-14)
    assert ghost[2]/ghost[0]==pytest.approx(.03)


def test_gauge_signal_dry_and_supercritical_inputs_rejected():
    s=Surface(np.zeros((2,2)),1,1)
    with pytest.raises(ValueError,match='Total gauge'):
        CharacteristicBoundary('east',(1,3),((0.,1.),),'m','fixture',1.,'total_gauge_stage').validate(s)
    with pytest.raises(ValueError,match='Wet'):wave_ghost([0,0,0],0,1,1,'east')
    with pytest.raises(ValueError,match='Subcritical'):wave_ghost([1,4,0],0,1,1,'east')
    with pytest.raises(ValueError,match='Dry incoming'):
        CharacteristicBoundary('east',(1,3),((0.,0.),),'m','fixture',1.).validate(s)


def test_changed_wave_background_cannot_restore_checkpoint():
    s=Surface(np.zeros((2,2)),1,1)
    def make(background):return Solver(s,depth=1,coastal=CharacteristicBoundary('east',(1,3),((0.,1.),),'m','fixture',background))
    original=make(1);cp=original.checkpoint()
    with pytest.raises(ValueError,match='checkpoint'):make(1.1).restore(cp)
