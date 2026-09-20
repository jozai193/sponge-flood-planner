import copy

from services.geodata.context import city_context
from services.geodata.landscape import add_landscape


def test_cover_is_general_and_excludes_buildings_water_and_nodata(monkeypatch):
    raster={'shape': [2,2],'values': [10,80,10,10],'valid_mask': [1,1,1,0],'sources': [],'coverage_fraction': .75}
    monkeypatch.setattr('services.geodata.landscape.cover_grid',lambda *args:raster)
    for crs in ('EPSG:32643','EPSG:32618','EPSG:32756'):
        manifest={'extent_m': 40,'grid': {'crs': crs,'origin_x_m': 100,'origin_y_m': 200},'buildings': [{'geometry': {'type': 'Polygon','coordinates': [[[-20,0],[0,0],[0,20],[-20,20],[-20,0]]]}}]}
        before=copy.deepcopy(manifest)
        result=add_landscape(manifest,{'trees': [],'roads': [],'assumptions': []})
        assert len(result['trees'])==1
        assert result['trees'][0]['basis']=='classified-cover'
        assert len(result['water'])==1
        assert result['water'][0]['polygon'][0]==[0,-20]
        assert manifest==before


def test_map_outage_does_not_erase_global_landscape(monkeypatch):
    def unavailable(*args):raise TimeoutError()
    monkeypatch.setattr('services.geodata.context.mapped_context',unavailable)
    monkeypatch.setattr('services.geodata.landscape.add_landscape',lambda m,c:{**c,'water':[1]})
    assert city_context({})['water']==[1]


def test_landcover_outage_preserves_inventory(monkeypatch):
    monkeypatch.setattr('services.geodata.context.mapped_context',lambda m:{'trees': [{'id': 'mapped'}],'assumptions': []})
    def unavailable(*args):raise TimeoutError()
    monkeypatch.setattr('services.geodata.landscape.add_landscape',unavailable)
    result=city_context({})
    assert result['trees']==[{'id': 'mapped'}]
    assert 'unavailable' in result['landscape_status']
