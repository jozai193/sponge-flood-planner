import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from services.geodata.enrichment import ApplyEvidenceRequest, EnrichmentRequest
from services.geodata.imports import validate_import
from services.geodata.merge import reconcile
from services.geodata.raster import sample_window


def feature(x):
    return {'type':'Feature','geometry':{'type':'Polygon','coordinates':[[[x,0],[x+1,0],[x+1,1],[x,1],[x,0]]]},'properties':{}}


def test_reconciliation_keeps_existing_overlap_without_duplicate():
    result,report=reconcile([feature(0)],[feature(.1),feature(3),feature(3)])
    assert len(result)==2
    assert report['overlapping_kept_existing']==2
    assert report['added']==1


def test_raster_orientation_and_nodata_are_preserved(tmp_path):
    path=tmp_path/'surface.tif'
    with rasterio.open(path,'w',driver='GTiff',width=2,height=2,count=1,dtype='int16',
                       crs='EPSG:4326',transform=from_origin(0,2,1,1),nodata=-999) as ds:
        ds.write(np.array([[10,20],[30,-999]],dtype='int16'),1)
    data,_=sample_window(path,np.array([[.5,1.5],[.5,1.5]]),np.array([[.5,.5],[1.5,1.5]]))
    assert data[0,0]==30 and data[1,0]==10 and data[1,1]==20
    assert np.isnan(data[0,1])


def test_enrichment_dates_and_material_acknowledgement():
    with pytest.raises(ValueError):EnrichmentRequest(start_date='2024-01-01')
    with pytest.raises(ValueError):EnrichmentRequest(start_date='2024-01-01',end_date='2024-02-01')
    with pytest.raises(ValueError):ApplyEvidenceRequest(landcover=True)


SOURCE={'title': 'Test survey','attribution': 'Test agency','observed_at': '2024-01-01T00:00:00Z',
            'horizontal_crs': 'EPSG:4326','vertical_datum': 'EGM2008','license': 'test fixture','provenance': 'surveyed'}


def test_drainage_requires_consistent_topology():
    survey={'kind': 'drainage','source': SOURCE,'nodes': [{'id': 'a','x': 0,'y': 0,'invert_m': 0,'ground_m': 1,'kind': 'inlet'}],
                'pipes': [{'id': 'p','from_node': 'a','to_node': 'missing','diameter_m': .5,'length_m': 20,'manning_n': .013}]}
    with pytest.raises(ValueError,match='missing node'):validate_import(survey)


def test_observations_require_depth():
    with pytest.raises(ValueError,match='depth_m'):
        validate_import({'kind': 'observations','source': SOURCE,'features': [feature(0)]})


def test_rainfall_preserves_nonuniform_intervals():
    survey=validate_import({'kind': 'rainfall','source': SOURCE,'storm': {'name': 'Measured event','duration_s': 60,
        'recession_s': 60,'depth_m': .003,'intervals': [{'start_s': 10,'end_s': 40,'rate_m_s': .0001}]}})
    assert survey.storm.intervals[0].start_s==10


def test_imerg_parser_integrates_half_hourly_fixture(tmp_path):
    import h5py

    from scripts.import_imerg import convert
    path=tmp_path/'3B-HHR.MS.MRG.3IMERG.20240101-S000000-E002959.0000.V07B.HDF5'
    with h5py.File(path,'w') as f:
        g=f.create_group('Grid');g.create_dataset('lon',data=[0.05,.15]);g.create_dataset('lat',data=[0.05,.15,.25])
        rain=g.create_dataset('precipitation',data=np.full((1,2,3),2.))
        rain.attrs['units']='mm/hr'
    survey=convert([path],.05,.05,SOURCE)
    assert survey['storm']['depth_m']==pytest.approx(.001)
    assert survey['storm']['duration_s']==1800


def test_dynamic_world_requires_configured_access(monkeypatch):
    from services.api.settings import settings
    from services.geodata.global_sources import dynamic_world
    monkeypatch.setattr(settings,'ee_project','')
    with pytest.raises(ValueError,match='Earth Engine'):dynamic_world({})


@pytest.mark.parametrize('missing',[False,True])
@pytest.mark.parametrize('surface_type',['bare_earth','topobathymetry'])
def test_terrain_import_rejects_missing_data_and_preserves_orientation(tmp_path,monkeypatch,missing,surface_type):
    from services.geodata import terrain_import as module
    folder=tmp_path/'bundle';folder.mkdir()
    manifest={'label': "Terrain fixture",'location': [3,0],'extent_m': 128,'grid': {'nx': 32,'ny': 32,'dx_m': 4,'dy_m': 4,
        'origin_x_m': 500000,'origin_y_m': 0,'crs': 'EPSG:32631'},'buildings': [],'sources': [],'assumptions': [],'quality': {}}
    (folder/'manifest.json').write_text(json.dumps(manifest))
    for name in ['roughness','infiltration','soil_capacity']:
        np.ones(1024,dtype='<f4').tofile(folder/f'{name}.bin')
    raster=tmp_path/'terrain.tif';offset=512 if surface_type=='topobathymetry' else 0;data=np.arange(1024,dtype='float32').reshape(32,32)-offset
    if missing:data[0,0]=-999
    with rasterio.open(raster,'w',driver='GTiff',width=32,height=32,count=1,dtype='float32',
        crs='EPSG:32631',transform=from_origin(500000,128,4,4),nodata=-999) as f:f.write(data,1)
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'prepare',lambda request,supplements:supplements)
    source={**SOURCE,'horizontal_crs':'EPSG:32631','surface_type':surface_type}
    if missing:
        with pytest.raises(ValueError,match='missing pixels'):module.import_terrain('bundle',raster,source)
    else:
        result=module.import_terrain('bundle',raster,source)
        assert result['terrain'][0]==992-offset
        assert result['sources'][-1]['surface_type']==surface_type
        assert min(result['terrain'])==-offset
        assert result['quality']['native_resolution_m']==4


def test_committed_provider_result_does_not_wait_for_native_teardown(tmp_path,monkeypatch):
    from services.api import database
    from services.geodata import enrichment as module
    updates=[];processes=[]
    monkeypatch.setattr(module,'EVIDENCE',tmp_path)
    monkeypatch.setattr(database,'update_resource',lambda resource,status,**fields:updates.append((status,fields)))
    class Process:
        def __init__(self,args,**kwargs):
            self.args=args;self.pid=123;self.returncode=None;processes.append(self)
            resource,_bundle,cap,attempt=args[-4:]
            (tmp_path/resource/f'{cap}.{attempt}.json').write_text(json.dumps({'note':'complete','coverage_fraction':1}))
        def poll(self):return self.returncode
        def kill(self):self.returncode=-9
        def wait(self,timeout):self.returncode=-9;return -9
    monkeypatch.setattr(module.subprocess,'Popen',Process)
    monkeypatch.setattr(module.subprocess,'run',lambda *args,**kwargs:None)
    module.enrichment_job('test-job','a'*64,{'capabilities':['landcover']})
    assert updates[-1][0]=='completed'
    assert updates[-1][1]['results']['landcover']['status']=='available'
    assert processes[0].returncode==-9


def test_storm_dates_do_not_restrict_satellite_observations_to_storm_day(monkeypatch):
    from services.geodata import global_sources
    from services.geodata.enrichment import run_one
    monkeypatch.setattr(global_sources,'dynamic_world',lambda m,start,end:(start,end))
    assert run_one({},'dynamic_world',{'start_date':'2024-08-06','end_date':'2024-08-06'})==(None,'2024-08-06')
