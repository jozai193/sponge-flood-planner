import numpy as np
import pytest

from services.geodata import prepare as preparation
from services.geodata import usgs


@pytest.mark.parametrize('covered',[True,False])
def test_auto_terrain_uses_full_coverage_or_records_fallback(tmp_path,monkeypatch,covered):
    monkeypatch.setattr(preparation,'ROOT',tmp_path)
    monkeypatch.setattr(preparation,'buildings',lambda bounds:([],[]))
    monkeypatch.setattr(preparation,'usgs_products',lambda bounds:([{'sourceId':'fixture'}],{}))
    def sample(*args):
        if not covered:raise ValueError('Partial raster coverage')
        return np.ones((32,32))*40,[],'fixture datum'
    monkeypatch.setattr(usgs,'sample_products',sample)
    monkeypatch.setattr(preparation,'terrarium',lambda lon,lat:(np.ones(lon.shape)*20,[]))
    m=preparation.prepare({'longitude': 77,'latitude': 13,'extent_m': 100,'grid_cells': 32,'source': 'auto','label': 'Test area','country_code': 'IN','currency': 'USD'})
    assert m['quality']['terrain_provider']==('usgs_1m' if covered else 'terrarium')
    assert bool(m['quality']['terrain_selection_note']) is (not covered)
    assert m['grid']['elevation_origin_m']==(40 if covered else 20)
    assert m['currency']=='INR'
    assert m['currency_source']=='geocoded_country'


def test_bundle_publication_is_content_addressed_and_detects_corruption(tmp_path,monkeypatch):
    monkeypatch.setattr(preparation,'ROOT',tmp_path)
    monkeypatch.setattr(preparation,'buildings',lambda bounds:([],[]))
    monkeypatch.setattr(preparation,'terrarium',lambda lon,lat:(np.ones(lon.shape)*20,[]))
    request={'longitude': 77,'latitude': 13,'extent_m': 100,'grid_cells': 32,'source': 'terrarium','label': 'Test area'}

    first=preparation.prepare(request)
    second=preparation.prepare(request)
    assert second['bundle_id']==first['bundle_id']
    assert (tmp_path/first['bundle_id']/'.').is_dir()

    (tmp_path/first['bundle_id']/'z.bin').write_bytes(b'corrupt')
    with pytest.raises(RuntimeError,match='missing or truncated'):
        preparation.prepare(request)
