import json

import pytest
from pyproj import Transformer

from services.geodata.context import mapped_context as city_context


def test_municipal_streets_preserve_inventory_vegetation(monkeypatch):
    x,y=Transformer.from_crs(4326,32618,always_xy=True).transform(-75.16,39.97)
    manifest={'extent_m':600,'grid':{'origin_x_m':x-300,'origin_y_m':y-300,'crs':'EPSG:32618'}}
    def fetch(url,params,**kwargs):
        assert kwargs["timeout_s"]==15
        if 'Street_Centerline' in url:
            return json.dumps({'features':[{'id':1,'properties':{'stname':'Test street'},'geometry':{'type':'LineString','coordinates':[[-75.161,39.97],[-75.159,39.97]]}}]}).encode(),{'source_url':url}
        return json.dumps({'features':[{'id':42,'properties':{},'geometry':{'type':'Point','coordinates':[-75.16,39.97]}}]}).encode(),{'source_url':url}
    monkeypatch.setattr('services.geodata.context.fetch',fetch)
    result=city_context(manifest)
    assert len(result['roads'])==1
    assert len(result['trees'])==1
    assert result['trees'][0]['id']=='philly-tree-42'
    assert result['vegetation_source']['source_url'].endswith('/query')


def test_vegetation_outage_preserves_streets_with_explicit_status(monkeypatch):
    x,y=Transformer.from_crs(4326,32618,always_xy=True).transform(-75.16,39.97)
    manifest={'extent_m':600,'grid':{'origin_x_m':x-300,'origin_y_m':y-300,'crs':'EPSG:32618'}}
    def fetch(url,params,**kwargs):
        assert kwargs["timeout_s"]==15
        if 'Street_Centerline' in url:return b'{"features":[]}',{'source_url':url}
        raise TimeoutError('Provider unavailable')
    monkeypatch.setattr('services.geodata.context.fetch',fetch)
    result=city_context(manifest)
    assert result['trees']==[]
    assert 'unavailable' in result['vegetation_status']
    assert result['attribution']=='City of Philadelphia street centerlines'


@pytest.mark.parametrize("bad_response", [b'{"remark":"timeout"}', b'{}', b'{"elements":null}', b'[]'])
def test_global_context_uses_bounded_fallback_for_incomplete_provider(monkeypatch,bad_response):
    x,y=Transformer.from_crs(4326,32643,always_xy=True).transform(77.68,12.91)
    calls=[]
    def fetch(url,params,**kwargs):
        calls.append((url,kwargs))
        return (bad_response if len(calls)==1 else b'{"elements":[]}'),{'source_url':url}
    monkeypatch.setattr('services.geodata.context.fetch',fetch)
    result=city_context({'extent_m':600,'grid':{'origin_x_m':x-300,'origin_y_m':y-300,'crs':'EPSG:32643'}})
    assert len(calls)==2
    assert all(options['timeout_s']==15 for _,options in calls)
    assert result['trees']==[]
