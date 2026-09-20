import numpy as np
import pytest

from services.reference.subgrid_storage import SubgridStorage


def test_narrow_channel_retains_storage_without_lowering_floodplain():
    z=np.full((4,4),2.);z[:,1]=-1.
    s=SubgridStorage(z,4,2.,3.)
    assert s.volume(0).item()==24.
    assert s.wet_area(0).item()==24.
    # Making the whole cell as low as its minimum fabricates four times the storage.
    assert (16*6*(0-z.min()))==4*s.volume(0).item()
    assert s.volume(3).item()==168.


def test_volume_inversion_across_wetting_levels_and_repeated_beds():
    z=np.array([[0.,0.,1.,2.],[0.,3.,1.,2.],[1.,1.,2.,2.],[1.,1.,2.,2.]])
    s=SubgridStorage(z,2,1.5,2.)
    for eta in (-1.,0.,.001,.5,1.,1.5,2.,3.,10.):
        v=s.volume(eta);restored=s.stage(v)
        np.testing.assert_allclose(s.volume(restored),v,atol=1e-13)
        np.testing.assert_allclose(restored[v>0],eta,atol=1e-13)


def test_total_storage_and_area_are_independent_of_coarse_partition():
    z=np.random.default_rng(982).normal(size=(12,16))
    for level in (-2.,0.,2.):
        expected=np.maximum(level-z,0).sum()*6
        for factor in (1,2,4):
            s=SubgridStorage(z,factor,2.,3.)
            assert s.volume(level).sum()==pytest.approx(expected,rel=1e-14)
            assert s.wet_area(level).sum()==((level>z).sum()*6)


def test_rotation_and_datum_shift_preserve_volumes():
    z=np.random.default_rng(44).uniform(-2,4,size=(8,12))
    a=SubgridStorage(z,4,2.,3.);b=SubgridStorage(np.rot90(z),4,3.,2.)
    c=SubgridStorage(z+19,4,2.,3.)
    np.testing.assert_allclose(np.rot90(a.volume(.7)),b.volume(.7))
    np.testing.assert_allclose(a.volume(.7),c.volume(19.7))


@pytest.mark.parametrize('bed,factor,dx,dy',[(np.zeros((3,4)),2,1,1),
    (np.array([[np.nan]]),1,1,1),(np.zeros((4,4)),True,1,1),
    (np.zeros((4,4)),2,-1,1)])
def test_invalid_terrain_rejected(bed,factor,dx,dy):
    with pytest.raises(ValueError): SubgridStorage(bed,factor,dx,dy)


def test_negative_volume_and_nonfinite_stage_rejected():
    s=SubgridStorage(np.zeros((2,2)),2,1,1)
    with pytest.raises(ValueError):s.stage(-.1)
    with pytest.raises(ValueError):s.volume(np.nan)
