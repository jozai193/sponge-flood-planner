import pytest
from fastapi import HTTPException

from services.api.main import geocode


def test_coordinates_work_without_geocoder():
    result=geocode({'query':'1.29, 103.85'},session_id='test')
    assert result['locations'][0]['latitude']==1.29
    assert result['locations'][0]['longitude']==103.85

def test_polar_coordinate_limit_is_explicit():
    result=geocode({'query':'89, 0'},session_id='test')
    assert result['locations'][0]['terrain_supported'] is False

def test_invalid_coordinates_rejected():
    with pytest.raises(HTTPException) as error:
        geocode({'query':'91, 0'},session_id='test')
    assert error.value.status_code==422

def test_signed_coordinates_ignore_city_hint():
    result=geocode({'query':'+12.9086945, +77.6625469','region':'Ignored'},session_id='test')
    assert result['locations'][0]['latitude']==12.9086945
    assert result['locations'][0]['terrain_supported'] is True
