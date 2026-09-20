import json

from services.geodata import city_buildings, providers


def test_global_buildings_use_broader_source(monkeypatch):
    monkeypatch.setattr(city_buildings,'acquire',lambda bounds:([{'id':'global'}],[{'provider':'Overture Maps'}]))
    features,sources=providers.buildings((81.8,25.4,81.9,25.5))
    assert features==[{'id':'global'}]
    assert sources[0]['provider']=='Overture Maps'

def test_global_failure_keeps_explicit_fallback(monkeypatch):
    def fail(bounds):raise TimeoutError()
    monkeypatch.setattr(city_buildings,'acquire',fail)
    monkeypatch.setattr(providers,'fetch',lambda *args:(json.dumps({'elements':[]}).encode(),{}))
    _features,sources=providers.buildings((81.8,25.4,81.9,25.5))
    assert sources[0]['provider']=='OpenStreetMap / Overpass'
    assert 'coverage may be incomplete' in sources[0]['coverage_note']

def test_cached_acquisition_avoids_network(tmp_path,monkeypatch):
    monkeypatch.setattr(city_buildings,'CACHE',tmp_path)
    city_buildings.cache_path((1,2,3,4)).write_text(json.dumps({'features':[{'id':'cached'}],'sources':[]}))
    assert city_buildings.acquire((1,2,3,4))==([{'id':'cached'}],[])
