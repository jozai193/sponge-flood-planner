import numpy as np
import pytest

from services.reference.observations import compare_peak_depths, compare_peak_elevations


def test_depth_comparison_rejects_wrong_event_and_absolute_elevations():
    m={'grid':{'nx': 2,'ny': 2,'crs': 'EPSG:3857','origin_x_m': 0,'origin_y_m': 0,'dx_m': 1,'dy_m': 1,'row_direction': 'north'}}
    f={'geometry':{'type':'Point','coordinates':[.5,.5]},'properties':{'depth_m':.3}}
    result=compare_peak_depths(m,np.full((2,2),.5),[f],'EPSG:3857','event-a','event-a')
    assert result['rmse_m']==pytest.approx(.2)
    with pytest.raises(ValueError,match='event ID'):compare_peak_depths(m,np.full((2,2),.5),[f],'EPSG:3857','event-a','event-b')
    f['properties']={'water_elevation_m':30}
    with pytest.raises(ValueError,match='local ground'):compare_peak_depths(m,np.full((2,2),.5),[f],'EPSG:3857','a','a')


def test_missing_vertical_reference_is_retained_without_invented_water_level():
    m={'grid':{'nx': 2,'ny': 2,'crs': 'EPSG:3857','origin_x_m': 0,'origin_y_m': 0,'dx_m': 1,'dy_m': 1,'row_direction': 'north','vertical_datum': 'NAVD88','elevation_origin_m': 10}}
    features=[{'geometry':{'type':'Point','coordinates':[.5,.5]},'properties':{'id':i,'water_elevation_m':level,'comparison_unavailable_reason':reason}}
              for i,level,reason in ((1,10.4,None),(2,None,'vertical_datum_unresolved'),(3,None,'measured_elevation_unavailable'))]
    args=(m,np.full((2,2),.5),np.zeros((2,2)),np.zeros((2,2)),features,'EPSG:3857','event','event','NAVD88')
    result=compare_peak_elevations(*args)
    assert result['total_count']==3 and result['compared_count']==1
    assert result['rmse_m']==pytest.approx(.1)
    assert [s['status'] for s in result['samples']]==['compared','vertical_datum_unresolved','measured_elevation_unavailable']
    assert all(s['observed_elevation_m'] is None and 'error_m' not in s for s in result['samples'][1:])
    features[1]['properties']['water_elevation_m']=10.4
    with pytest.raises(ValueError,match='datum-assumed'):compare_peak_elevations(*args)


def test_elevation_audit_preserves_dry_misses_and_building_exclusions():
    m={'grid':{'nx': 2,'ny': 2,'crs': 'EPSG:3857','origin_x_m': 0,'origin_y_m': 0,
                   'dx_m': 1,'dy_m': 1,'row_direction': 'north','vertical_datum': 'NAVD88','elevation_origin_m': 10}}
    features=[{'geometry':{'type':'Point','coordinates':xy},
               'properties':{'water_elevation_m':10.4,'id':i,'site_id':i}}
              for i,xy in enumerate([[.5,.5],[1.5,.5],[.5,1.5],[3,3]])]
    peak=np.array([[.5,0],[.5,.5]])
    mask=np.array([[0,0],[1,0]])
    r=compare_peak_elevations(m,peak,np.zeros((2,2)),mask,features,'EPSG:3857','sandy','sandy','NAVD88')
    assert [x['status'] for x in r['samples']]==['compared','observed_flood_model_dry','building_cell_unresolved','outside_domain']
    assert r['rmse_m']==pytest.approx(.1)
    assert r['missed_flood_count']==1
    assert 'predicted_elevation_m' not in r['samples'][1]
    for datum,event in [('MSL','sandy'),('NAVD88','another-event')]:
        with pytest.raises(ValueError):
            compare_peak_elevations(m,peak,np.zeros((2,2)),mask,features,'EPSG:3857','sandy',event,datum)


def test_indoor_mark_is_not_scored_at_a_wet_outdoor_survey_coordinate():
    m={'grid':{'nx': 2,'ny': 2,'crs': 'EPSG:3857','origin_x_m': 0,'origin_y_m': 0,
                   'dx_m': 1,'dy_m': 1,'row_direction': 'north','vertical_datum': 'NAVD88','elevation_origin_m': 0}}
    feature={'geometry':{'type':'Point','coordinates':[.5,.5]},
             'properties':{'water_elevation_m':.4,'id':34781,'site_id':27782,'interior':True}}
    r=compare_peak_elevations(m,np.full((2,2),.5),np.zeros((2,2)),np.zeros((2,2)),
        [feature],'EPSG:3857','michael','michael','NAVD88')
    assert r['samples'][0]['status']=='interior_observation_unsupported'
    assert r['total_count']==1 and r['compared_count']==0
    assert r['rmse_m'] is None
    assert 'predicted_elevation_m' not in r['samples'][0]
    feature['properties'].update(interior=False,observation_eligibility='unresolved')
    r=compare_peak_elevations(m,np.full((2,2),.5),np.zeros((2,2)),np.zeros((2,2)),
        [feature],'EPSG:3857','michael','michael','NAVD88')
    assert r['samples'][0]['status']=='observation_setting_unresolved'
    assert r['rmse_m'] is None
