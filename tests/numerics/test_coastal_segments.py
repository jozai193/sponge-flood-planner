import numpy as np
import pytest

from services.api.contracts import SolverConfig
from services.reference.coastal import CoastalBoundary
from services.reference.coastal_segments import CoastalSegments
from services.reference.solver import Solver as Original
from services.reference.solver_segments_candidate import Solver, Surface


def segment(edge, levels, nx=8, ny=4, datum='local metres'):
    cells={'west':tuple(r*nx for r in range(ny)), 'east':tuple(r*nx+nx-1 for r in range(ny)),
           'south':tuple(range(nx)), 'north':tuple(range((ny-1)*nx,ny*nx))}[edge]
    return CoastalBoundary(edge,cells,levels,datum,'synthetic fixture')


def test_one_segment_matches_frozen_original_exactly():
    s=Surface(np.zeros((4,8)),1,1,roughness=.035)
    b=segment('west',((0.,.2),(1.,.3),(2.,.2)))
    old=Original(s,SolverConfig(spatial_order=2,dt_max_s=.03),depth=.2,coastal=b)
    new=Solver(s,old.config,depth=.2,coastal=CoastalSegments((('west tide',b),)))
    for time in (.7,1.3,2.):
        old.advance(time);new.advance(time)
        np.testing.assert_array_equal(old.u,new.u)
        assert old.ledger()==new.ledger()
    assert new.boundary_volumes['west tide']==pytest.approx([new.inflow_volume,new.outflow_volume])


def test_four_edges_at_rest_on_irregular_bed():
    z=np.arange(32).reshape(4,8)*.003
    s=Surface(z,1,1,roughness=0)
    bs=CoastalSegments(tuple((e,segment(e,((0.,.4),))) for e in ('west','east','south','north')))
    sim=Solver(s,SolverConfig(spatial_order=2),depth=bs.initial_depth(s),coastal=bs)
    sim.advance(1)
    np.testing.assert_allclose(sim.u[...,0],.4-z,atol=1e-14)
    np.testing.assert_allclose(sim.u[...,1:],0,atol=1e-14)
    assert sim.ledger()['relative_residual']<1e-12


def test_two_ended_channel_flows_and_accounts_for_both_boundaries():
    s=Surface(np.zeros((4,8)),1,1,roughness=.035)
    bs=CoastalSegments((('upstream',segment('west',((0.,.4),))),('downstream',segment('east',((0.,.2),)))))
    sim=Solver(s,SolverConfig(spatial_order=2,dt_max_s=.03),depth=.3,coastal=bs)
    sim.advance(2)
    assert sim.u[...,1].mean()>0
    assert sim.boundary_volumes['upstream'][0]>0
    assert sim.boundary_volumes['downstream'][1]>0
    assert sum(v[0] for v in sim.boundary_volumes.values())==pytest.approx(sim.inflow_volume)
    assert sum(v[1] for v in sim.boundary_volumes.values())==pytest.approx(sim.outflow_volume)
    assert sim.ledger()['relative_residual']<1e-12
    with pytest.raises(ValueError,match='explicit initial'):bs.initial_depth(s)


def test_checkpoint_preserves_segment_ledgers_and_rejects_changed_forcing():
    s=Surface(np.zeros((4,8)),1,1,roughness=0)
    b=segment('west',((0.,.2),(.37,.4),(2.,.2)))
    bs=CoastalSegments((('tide',b),))
    a=Solver(s,depth=.2,coastal=bs);a.advance(.73);cp=a.checkpoint();a.advance(1.4)
    c=Solver(s,depth=.2,coastal=bs);c.restore(cp);c.advance(1.4)
    np.testing.assert_array_equal(a.u,c.u)
    assert a.boundary_volumes==c.boundary_volumes
    assert cp['boundary_volumes']!=a.boundary_volumes
    wrong=Solver(s,depth=.2,coastal=segment('west',((0.,.3),)))
    with pytest.raises(ValueError,match='checkpoint'):wrong.restore(cp)


def test_multi_segment_flow_rotates_with_anisotropic_cells():
    config=SolverConfig(spatial_order=2,dt_max_s=.02)
    sims=[]
    for nx,ny,dx,dy,edges in [(8,4,1.,2.,('west','east')),(4,8,2.,1.,('south','north'))]:
        bs=CoastalSegments(tuple((str(i),segment(edge,((0.,level),(.37,level+.04),(2.,level)),nx,ny))
                                  for i,(edge,level) in enumerate(zip(edges,(.4,.2)))))
        sim=Solver(Surface(np.zeros((ny,nx)),dx,dy,roughness=.035),config,depth=.3,coastal=bs)
        sim.advance(1);sims.append(sim)
    np.testing.assert_allclose(sims[0].u[...,0].T,sims[1].u[...,0],atol=1e-13)
    np.testing.assert_allclose(sims[0].u[...,1].T,sims[1].u[...,2],atol=1e-13)
    for name in ('0','1'):
        np.testing.assert_allclose(sims[0].boundary_volumes[name],sims[1].boundary_volumes[name],atol=1e-12)


def test_partial_boundaries_leave_other_faces_closed_and_split_initial_basins():
    z=np.zeros((4,8));z[:,3]=2
    s=Surface(z,1,1,roughness=0)
    left=CoastalBoundary('west',(0,),((0.,.4),),'local metres','test')
    right=CoastalBoundary('east',(31,),((0.,.4),),'local metres','test')
    bs=CoastalSegments((('left',left),('right',right)))
    depth=bs.initial_depth(s)
    assert np.all(depth[:,3]==0) and np.all(depth[:,:3]==.4) and np.all(depth[:,4:]==.4)
    sim=Solver(s,SolverConfig(spatial_order=2),depth=depth,coastal=bs)
    sim.advance(1)
    np.testing.assert_allclose(sim.u[...,0],depth,atol=1e-14)
    assert sim.inflow_volume<1e-12 and sim.outflow_volume<1e-12


@pytest.mark.parametrize('failure',['duplicate','name','datum'])
def test_ambiguous_boundaries_rejected(failure):
    s=Surface(np.zeros((4,8)),1,1)
    b=segment('west',((0.,.2),))
    if failure=='duplicate':bs=CoastalSegments((('a',b),('b',b)))
    elif failure=='name':bs=CoastalSegments((('a',b),('a',segment('east',((0.,.2),)))))
    else:bs=CoastalSegments((('a',b),('b',segment('east',((0.,.2),),datum='different datum'))))
    with pytest.raises(ValueError):Solver(s,coastal=bs)
