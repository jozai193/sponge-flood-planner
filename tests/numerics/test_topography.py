import numpy as np

from services.geodata.topography import terrain_metrics
from services.reference.solver import Solver, Surface


def test_bowl_storage_and_vertical_offset_invariance():
    z=np.ones((7,7))*2;z[1:-1,1:-1]=0
    before=z.copy();a=terrain_metrics(z,2,3);b=terrain_metrics(z+900,2,3)
    assert a['depression_storage_m3']==300
    assert a['deepest_depression_m']==2
    assert b['depression_storage_m3']==a['depression_storage_m3']
    np.testing.assert_array_equal(z,before)


def test_downhill_slope_is_not_a_closed_depression():
    z=np.tile(np.arange(8,dtype=float),(6,1))
    assert terrain_metrics(z,1,1)['depression_storage_m3']==0
    sim=Solver(Surface(z*.02,1,1,roughness=0),depth=.1)
    sim.advance(1)
    assert sim.u[:,0,0].mean()>sim.u[:,-1,0].mean()
    assert abs(sim.ledger()['residual_m3'])<1e-9


def test_closed_bowl_ponds_without_climbing_higher_terrain():
    z=np.ones((8,8));z[2:6,2:6]=0
    h=np.zeros_like(z);h[2:6,2:6]=.4
    sim=Solver(Surface(z,1,1,roughness=0),depth=h)
    sim.advance(2)
    np.testing.assert_allclose(sim.u[...,0],h,atol=1e-10)


def test_building_enclosed_cells_are_not_given_a_false_spill_level():
    z=np.zeros((7,7));walls=np.zeros_like(z,dtype=bool)
    walls[1:6,1]=True;walls[1:6,5]=True;walls[1,1:6]=True;walls[5,1:6]=True
    assert terrain_metrics(z,1,1,walls)['unresolved_enclosed_area_m2']==9
