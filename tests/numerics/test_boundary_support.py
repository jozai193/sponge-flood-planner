import numpy as np
import pytest

from services.reference.boundary_support import boundary_support


def points():
    return [{'edge': e,'face_index': i,'levels_m_model_msl': [0.,.1]}
            for e in ('west','east','south','north') for i in range(2)]


def test_dry_zero_level_is_valid_but_missing_values_are_not():
    p=points();p[0]['levels_m_model_msl'][0]=None
    r=boundary_support(np.full((2,2),-1.),p,[0],2)[0]
    assert r['below_reference_faces']==8 and r['unsupported_faces']==1


def test_datum_changes_potential_wet_support_without_filling_gaps():
    p=points();p[0]['levels_m_model_msl'][0]=float('nan')
    r=boundary_support(np.full((2,2),-.05),p,[-.1,0],2)
    assert [v['unsupported_faces'] for v in r]==[0,1]


@pytest.mark.parametrize('failure',['duplicate','missing','sample_count','bad_terrain'])
def test_malformed_inventory_fails_closed(failure):
    p=points();z=np.zeros((2,2))
    if failure=='duplicate':p.append(p[0])
    if failure=='missing':p.pop()
    if failure=='sample_count':p[0]['levels_m_model_msl'].pop()
    if failure=='bad_terrain':z[0,0]=np.nan
    with pytest.raises(ValueError):boundary_support(z,p,[0],2)
