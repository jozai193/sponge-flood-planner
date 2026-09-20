import pytest

from services.reference.validation_regression import compare_assessments


def run(errors):
    return {'event_id': 'event-a', 'mass_gate_passed': True, 'samples': [
        {'observation_id': i, 'observed_elevation_m': 2., 'status': 'compared' if e is not None else 'observed_flood_model_dry', 'error_m': e}
        for i, e in enumerate(errors)]}


def test_dropping_worst_prediction_cannot_appear_to_improve():
    result = compare_assessments(run([.1, 1.]), run([.05, None]))
    assert result['candidate_common_rmse_m'] < result['baseline_common_rmse_m']
    assert result['lost_wet_ids'] == [1]
    assert not result['regression_gate_passed']


def test_reclassifying_a_dry_miss_as_unresolved_cannot_pass():
    baseline=run([.1,None]);candidate=run([.05,None])
    candidate['samples'][1]['status']='building_cell_unresolved'
    result=compare_assessments(baseline,candidate)
    assert result['dry_after']<result['dry_before']
    assert result['lost_supported_ids']==[1]
    assert not result['regression_gate_passed']


def test_retained_missing_datum_is_not_a_zero_error_observation():
    baseline=run([.2]);candidate=run([.1])
    for r in (baseline,candidate):
        r['samples'].append({'observation_id': 9,'observed_elevation_m': None,'status': 'vertical_datum_unresolved'})
    result=compare_assessments(baseline,candidate)
    assert result['common_wet_ids']==[0] and result['regression_gate_passed']
    assert result['candidate_common_rmse_m']==pytest.approx(.1)
    candidate['samples'][1]['status']='compared'
    with pytest.raises(ValueError,match='Nonfinite observation'):compare_assessments(baseline,candidate)


def test_improvement_requires_numerical_gate_and_identical_observations():
    assert compare_assessments(run([.2, .4]), run([.1, .3]))['regression_gate_passed']
    candidate = run([.1, .3])
    candidate['mass_gate_passed'] = False
    assert not compare_assessments(run([.2, .4]), candidate)['regression_gate_passed']
    candidate['samples'][0]['observed_elevation_m'] = 2.1
    with pytest.raises(ValueError, match='values changed'):
        compare_assessments(run([.2, .4]), candidate)
    with pytest.raises(ValueError, match='cohort changed'):
        compare_assessments(run([.2, .4]), run([.1]))
    with pytest.raises(ValueError, match='Nonfinite prediction'):
        compare_assessments(run([float('inf')]), run([.1]))


def test_repeated_easy_site_cannot_hide_regression_at_another_site():
    baseline=run([.5]*9+[.1]);candidate=run([0.]*9+[.8])
    for r in (baseline,candidate):
        for i,s in enumerate(r['samples']):s['site_id']='a' if i<9 else 'b'
    result=compare_assessments(baseline,candidate)
    assert result['candidate_common_rmse_m']<result['baseline_common_rmse_m']
    assert result['candidate_common_site_rmse_m']>result['baseline_common_site_rmse_m']
    assert not result['regression_gate_passed']
    candidate['samples'][0]['site_id']='other'
    with pytest.raises(ValueError,match='site membership'):
        compare_assessments(baseline,candidate)
