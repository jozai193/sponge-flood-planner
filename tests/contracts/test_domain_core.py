import numpy as np
import pytest

from scripts.compare_domain_experiment import verify_core


def fixture():
    old={'nx': 2,'ny': 2,'origin_x_m': 2.,'origin_y_m': 3.,'dx_m': 2.,'dy_m': 3.,'crs': 'EPSG:32617','elevation_origin_m': -19.,'row_direction': 'north','vertical_datum': 'NAVD88'}
    new={**old,'nx':4,'ny':4,'origin_x_m':0.,'origin_y_m':0.}
    z=np.arange(4,dtype='f4').reshape(2,2);large=np.zeros((4,4),dtype='f4');large[1:3,1:3]=z
    solid=np.zeros((2,2),dtype='u1');mask=np.zeros((4,4),dtype='u1')
    return old,new,z,large,solid,mask

def test_domain_core_accepts_exact_aligned_terrain_and_masks():
    assert verify_core(*fixture())==(1,1)

@pytest.mark.parametrize('change,message',[('bed','terrain'),('solid','buildings'),('offset','aligned'),('datum','convention')])
def test_domain_core_rejects_hidden_changes(change,message):
    old,new,z,large,solid,mask=fixture()
    if change=='bed':large[1,1]=np.nextafter(np.float32(0),np.float32(1))
    if change=='solid':mask[1,1]=1
    if change=='offset':new['origin_x_m']=.1
    if change=='datum':new['elevation_origin_m']=-20
    with pytest.raises(ValueError,match=message):verify_core(old,new,z,large,solid,mask)
