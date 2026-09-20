import numpy as np
import pytest

from services.api.contracts import SolverConfig
from services.reference.coastal import CoastalBoundary
from services.reference.momentum_diagnostic import MomentumDiagnosticSolver
from services.reference.solver_segments_candidate import Solver, Surface


def test_full_momentum_switch_reproduces_original_with_open_boundary():
    z=np.zeros((4,16)); wall=np.zeros_like(z,dtype=bool);wall[1,8]=True
    boundary=CoastalBoundary('west',tuple(r*16 for r in range(4)),((0.,.1),(2.,.15)), 'local metres','test')
    surface=Surface(z,1,1,solid=wall)
    config=SolverConfig(spatial_order=2,dt_max_s=.02)
    a=Solver(surface,config,depth=.1,coastal=boundary)
    b=MomentumDiagnosticSolver(surface,config,depth=.1,coastal=boundary)
    a.advance(3);b.advance(3)
    np.testing.assert_array_equal(a.u,b.u)
    assert a.ledger()==b.ledger()


@pytest.mark.parametrize('advection',[True,False])
def test_still_lake_remains_still_and_closed(advection):
    s=MomentumDiagnosticSolver(Surface(np.zeros((4,12)),1,1),depth=.2,advective_momentum=advection)
    before=s.u.copy();s.advance(2)
    np.testing.assert_array_equal(s.u,before)
    assert s.ledger()['relative_residual']==0


def test_no_advection_closed_smooth_pulse_conserves_mass_and_rotates():
    h=np.full((4,16),.1);h[:,5:9]=.12
    a=MomentumDiagnosticSolver(Surface(np.zeros_like(h),1,1),depth=h,advective_momentum=False)
    b=MomentumDiagnosticSolver(Surface(np.zeros_like(h.T),1,1),depth=h.T,advective_momentum=False)
    a.advance(3);b.advance(3)
    np.testing.assert_allclose(a.u[...,0].T,b.u[...,0],atol=1e-14)
    assert a.ledger()['relative_residual']<1e-13


def test_advective_flux_is_removed_in_uniform_moving_water():
    z=np.zeros((4,8));surface=Surface(z,1,1,roughness=0)
    a=MomentumDiagnosticSolver(surface,depth=.5)
    b=MomentumDiagnosticSolver(surface,depth=.5,advective_momentum=False)
    a.u[...,1]=b.u[...,1]=.2;a.u[...,2]=b.u[...,2]=.1
    fa=a._faces(a.u,1)[0][2,4];fb=b._faces(b.u,1)[0][2,4]
    np.testing.assert_allclose(fa-fb,[0.,.2*.2/.5,.2*.1/.5],atol=1e-14)
