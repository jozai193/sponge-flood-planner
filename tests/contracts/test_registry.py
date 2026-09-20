import pytest

from services.geodata.registry import select_provider


@pytest.mark.parametrize('bounds', [(77.64,12.91,77.66,12.93),(151.1,-33.9,151.2,-33.8),(-.2,51.4,-.1,51.5)])
def test_shared_global_adapter(bounds):
    assert select_provider('buildings', bounds).id == 'osm_buildings'


def test_regional_adapter_requires_entire_extent():
    assert select_provider('buildings', (-75.2,39.9,-75.1,40)).id == 'philadelphia_buildings'
    assert select_provider('buildings', (-75.2,39.9,-74.8,40)).id == 'osm_buildings'


def test_wrapped_extent_is_not_silently_misrouted():
    with pytest.raises(ValueError, match='full extent'):
        select_provider('buildings', (179.9,-20,-179.9,-19.9))
