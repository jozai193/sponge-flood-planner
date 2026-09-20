import pytest

from services.reference.site_metrics import site_balanced_errors


def test_repeated_marks_do_not_increase_a_sites_weight():
    samples=[{'status': 'compared','site_id': site,'observation_id': i,'error_m': e,'observed_elevation_m': 1.}
             for i,(site,e) in enumerate([('a',1.),('a',1.),('b',0.)])]
    result=site_balanced_errors(samples,1.)
    assert result['site_groups']==2 and result['mark_count']==3
    assert result['rmse_m']==pytest.approx((.5)**.5)
    assert result['gauge_only_rmse_m']==0
    samples[1]['error_m']=-1
    assert site_balanced_errors(samples)['rmse_m']==result['rmse_m']


def test_unknown_sites_remain_separate_and_dry_marks_stay_unscored():
    samples=[{'status': 'compared','site_id': None,'observation_id': i,'error_m': e,'observed_elevation_m': 1.} for i,e in enumerate([1.,0.])]
    samples.append({'status': 'observed_flood_model_dry','site_id': 'c','observation_id': 3})
    assert site_balanced_errors(samples)['site_groups']==2
    assert site_balanced_errors(samples)['unassigned_site_marks']==2
