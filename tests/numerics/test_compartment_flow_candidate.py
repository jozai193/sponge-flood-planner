import numpy as np
import pytest

from services.reference.compartment_flow_candidate import CompartmentFlow, build_graph


def fixture():
    z=np.zeros((8,16));wall=np.ones(z.shape,bool);wall[4:6,:]=False;wall[7,5:7]=False
    return z,wall


def test_isolated_pool_in_same_coarse_cell_has_separate_storage():
    z,w=fixture();g=build_graph(z,w,4)
    assert g.labels[4,5]!=g.labels[7,5]
    stage=np.full(len(g.area),.5);pool=g.labels[7,5];stage[pool]=0
    s=CompartmentFlow(g,stage,{'west':lambda t:.6})
    s.advance(5)
    assert s.volume[pool]==0
    assert s.ledger()['relative_residual']<1e-13
    assert s.ledger()['inflow_m3']>0


def test_face_width_and_storage_count_only_open_pixels():
    z,w=fixture();g=build_graph(z,w,4,2,3)
    assert all(link[2]==6 for link in g.links)
    assert g.area.sum()==np.sum(~w)*6


def test_barrier_splits_compartment_even_inside_coarse_cell():
    z,w=fixture();w[:,6]=True;g=build_graph(z,w,4)
    s=CompartmentFlow(g,.5,{'west':lambda t:.7})
    before=s.volume.copy();s.advance(5)
    downstream=np.unique(g.labels[:,7:]);downstream=downstream[downstream>=0]
    np.testing.assert_array_equal(s.volume[downstream],before[downstream])


def test_still_water_lake_exact_and_closed_mass():
    z,w=fixture();g=build_graph(z,w,4)
    s=CompartmentFlow(g,.5);before=s.volume.copy();s.advance(3)
    np.testing.assert_array_equal(s.volume,before)
    np.testing.assert_array_equal(s.q,0)


def test_rotation_preserves_depth_and_ledger():
    z,w=fixture();a=CompartmentFlow(build_graph(z,w,4),.5,{'west':lambda t:.6})
    b=CompartmentFlow(build_graph(np.rot90(z),np.rot90(w),4),.5,{'north':lambda t:.6})
    # np.rot90 maps column zero to the last row (north in solver coordinates).
    a.advance(2);b.advance(2)
    np.testing.assert_allclose(np.rot90(a.fine_depth()),b.fine_depth(),atol=1e-14)
    assert a.ledger()['stored_m3']==pytest.approx(b.ledger()['stored_m3'],abs=1e-12)


def test_dry_start_limiter_preserves_nonnegative_mass():
    z,w=fixture();s=CompartmentFlow(build_graph(z,w,4),0.,{'west':lambda t:.2})
    s.advance(10)
    assert s.volume.min()>=0 and s.ledger()['inflow_m3']>0
    assert s.ledger()['relative_residual']<1e-12


def test_shared_outgoing_limit_uses_available_volume_and_accounts_every_transfer():
    z,w=fixture();s=CompartmentFlow(build_graph(z,w,4),.01,roughness=0)
    s.q[:]=1e6
    before=s.volume.sum();s.step(.1)
    assert s.limited_steps==1
    assert np.all(s.volume>=0)
    assert s.volume.sum()==pytest.approx(before,abs=1e-14)
    assert s.ledger()['relative_residual']<1e-14


def test_internal_sills_are_rejected_instead_of_short_circuited():
    z,w=fixture();z[4,5]=.1
    with pytest.raises(ValueError,match='sill'):build_graph(z,w,4)


def test_nonfinite_forcing_rejected_without_state_mutation():
    z,w=fixture();s=CompartmentFlow(build_graph(z,w,4),.5,{'west':lambda t:np.nan})
    before=s.volume.copy()
    with pytest.raises(ValueError):s.step(.01)
    np.testing.assert_array_equal(s.volume,before)
    assert s.time==0
