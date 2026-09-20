import numpy as np

from scripts.diagnose_domain_connectivity import access_levels


def test_access_uses_lowest_barrier_rather_than_shortest_route():
    # The direct middle row crosses height 5; the longer upper route crosses 2.
    bed=np.array([[2.,2.,2.],[0.,5.,0.],[9.,9.,9.]])
    solid=np.zeros((3,3),bool)
    result=access_levels(bed,solid,(5,))
    assert result[1,0]==2.
    assert result[1,2]==0.


def test_buildings_block_access_and_bed_can_be_below_datum():
    bed=np.full((3,3),-2.);solid=np.zeros((3,3),bool);solid[:,1]=True
    result=access_levels(bed,solid,(5,))
    assert np.isinf(result[:,:2]).all()
    assert (result[:,2]==-2.).all()
