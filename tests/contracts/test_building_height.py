import pytest

from services.geodata.building_height import building_height, philadelphia_height_properties


@pytest.mark.parametrize('field',['approx_hgt','APPROX_HGT'])
def test_philadelphia_feet_are_normalized_only_by_its_adapter(field):
    raw={field:47,'max_hgt':49.9,'base_elevation':70.65}
    normalized=philadelphia_height_properties(raw)
    height,source=building_height(normalized)
    assert height==pytest.approx(14.3256)
    assert 'approximate height' in source
    assert 'height' not in raw
    assert building_height(raw)==(9,'assumed display height')

@pytest.mark.parametrize('value',[0,-2,None,True,'bad',float('nan')])
def test_invalid_municipal_height_preserves_explicit_fallback(value):
    assert building_height(philadelphia_height_properties({'approx_hgt':value}))==(9,'assumed display height')
@pytest.mark.parametrize('value,expected', [('12.5',12.5),('12 m',12),('30 ft',9.144),(18,18)])
def test_sourced_height(value,expected):
    height,source=building_height({'height':value})
    assert height==pytest.approx(expected)
    assert source.startswith('provider')
@pytest.mark.parametrize('properties', [{'building:levels':'4'},{'num_floors':4}])
def test_floor_estimate_is_explicit(properties):
    assert building_height(properties)==(12,'estimated from mapped floors at assumed 3 m per floor')
@pytest.mark.parametrize('value',[None,True,-2,'bad','nan','12;15',float('inf')])
def test_invalid_heights_do_not_create_invalid_geometry(value):
    assert building_height({'height':value})==(9,'assumed display height')
