import numpy as np
import pytest

from services.api.contracts import SolverConfig
from services.reference.coastal import CoastalBoundary
from services.reference.solver import Solver, Surface


def boundary(edge,levels):
    cells={'west':(0,4,8,12),'east':(3,7,11,15),'south':(0,1,2,3),'north':(12,13,14,15)}[edge]
    return CoastalBoundary(edge,cells,levels,'local metres','analytic verification')


@pytest.mark.parametrize('edge',['west','east','south','north'])
def test_coastal_lake_at_rest_is_exact_on_irregular_bed(edge):
    z=np.array([[0,.2,.1,0],[.1,.4,.3,.1],[0,.2,.5,0],[.1,0,.2,.1]])
    s=Surface(z,10,10,roughness=0);b=boundary(edge,((0.,1.),))
    solver=Solver(s,SolverConfig(spatial_order=2),depth=b.initial_depth(s),coastal=b)
    solver.advance(5)
    np.testing.assert_allclose(solver.u[...,0],1-z,atol=1e-12)
    np.testing.assert_allclose(solver.u[...,1:],0,atol=1e-12)
    assert solver.ledger()['relative_residual']<1e-12


def test_rising_and_falling_tide_rotates_and_accounts_for_return_flow():
    outputs=[]
    for edge in ('west','east','south','north'):
        s=Surface(np.zeros((4,4)),2,2,roughness=.035)
        b=boundary(edge,((0.,.2),(10.,.6),(20.,.2),(30.,.2)))
        solver=Solver(s,SolverConfig(spatial_order=2,dt_max_s=.05),depth=.2,coastal=b)
        solver.advance(30)
        ledger=solver.ledger()
        assert ledger['inflow_m3']>0 and ledger['outflow_m3']>0
        assert ledger['relative_residual']<1e-10
        outputs.append(solver.u[...,0])
    np.testing.assert_allclose(outputs[0],np.fliplr(outputs[1]),atol=1e-12)
    np.testing.assert_allclose(outputs[0],outputs[2].T,atol=1e-12)
    np.testing.assert_allclose(outputs[0],np.flipud(outputs[3]).T,atol=1e-12)


def test_coastal_initialization_keeps_isolated_basin_dry_and_checks_cells():
    z=np.zeros((4,4));z[:,1]=2;s=Surface(z,1,1)
    b=boundary('west',((0.,1.),))
    expected=np.zeros((4,4));expected[:,0]=1
    np.testing.assert_array_equal(b.initial_depth(s),expected)
    with pytest.raises(ValueError,match='edge'):
        CoastalBoundary('south',(8,),((0.,1.),),'m','test').validate(s)
