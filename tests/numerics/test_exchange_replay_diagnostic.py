import numpy as np
import pytest

from services.api.contracts import SolverConfig
from services.reference.coastal import CoastalBoundary
from services.reference.compartment_flow_candidate import CompartmentFlow, build_graph
from services.reference.exchange_replay_diagnostic import BoundaryRecordingHLL, ExchangeReplayGraph
from services.reference.solver_segments_candidate import Solver, Surface


def test_unprescribed_copy_is_exact():
    g=build_graph(np.zeros((2,8)),np.zeros((2,8),bool),1)
    a=CompartmentFlow(g,.1,{'west':lambda t:.2});b=ExchangeReplayGraph(g,.1,{'west':lambda t:.2})
    a.advance(1);b.advance(1)
    np.testing.assert_array_equal(a.volume,b.volume)
    assert a.ledger()==b.ledger()


def test_prescribed_flux_changes_storage_by_exact_exchange():
    g=build_graph(np.zeros((2,8)),np.zeros((2,8),bool),1)
    s=ExchangeReplayGraph(g,0.,{'west':lambda t:0.,'east':lambda t:0.})
    s.prescribed_boundary_q=np.array([-.1,-.2,0.,0.]);s.step(.1)
    assert s.volume.sum()==pytest.approx(.03)
    assert s.max_boundary_flux_adjustment==0
    assert s.ledger()['relative_residual']<1e-14


def test_unavailable_outflow_is_reported_as_unmatched():
    g=build_graph(np.zeros((2,8)),np.zeros((2,8),bool),1)
    s=ExchangeReplayGraph(g,0.,{'west':lambda t:0.})
    s.prescribed_boundary_q=np.array([.1,.2]);s.step(.1)
    assert s.max_boundary_flux_adjustment==pytest.approx(.2)
    assert s.volume.sum()==0


def test_recording_hll_is_exact_and_signed_flux_reconciles_storage():
    surface=Surface(np.zeros((2,8)),1,1)
    boundary=CoastalBoundary('west',(0,8),((0.,.2),),'local metres','test')
    config=SolverConfig(dt_max_s=.01)
    a=Solver(surface,config,depth=.1,coastal=boundary)
    b=BoundaryRecordingHLL(surface,config,depth=.1,coastal=boundary);b.open_rows=np.array([0,1])
    start=b.storage();dt=b.step(.01);a.step(.01)
    np.testing.assert_array_equal(a.u,b.u)
    assert b.storage()-start==pytest.approx(-b.mean_boundary_q.sum()*dt,abs=1e-14)
