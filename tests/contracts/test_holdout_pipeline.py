"""Exercise the actual held-out scoring/report scripts with synthetic evidence."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def test_holdout_report_retains_lost_good_mark_and_unknown_datum(tmp_path):
    repo=Path(__file__).resolve().parents[2]
    protocol={'event_id': 'synthetic-pipeline-fixture','limitations': ['Synthetic evidence; not a historical result.']}
    raw=json.dumps(protocol).encode();digest=hashlib.sha256(raw).hexdigest()
    (tmp_path/'protocol.json').write_bytes(raw)
    (tmp_path/'protocol.sha256').write_text(digest)
    (tmp_path/'evaluation-plan.json').write_text(json.dumps({'observed_high_water_elevations_inspected': False,
        'comparison_rules': {'common_point_and_equal_site_rmse_worsening_tolerance_m': .01}}))
    samples=[{'observation_id': i,'site_id': i,'quality': q,'quality_description': 'Synthetic quality',
        'observed_elevation_m': 2.,'status': 'compared','predicted_elevation_m': 2.+e,'error_m': e}
        for i,q,e in ((16663,4,.2),(16667,4,.2),(16664,4,.2),(16723,2,1.))]
    samples.append({'observation_id': 16666,'site_id': 16666,'quality': 2,'quality_description': 'Synthetic quality',
        'observed_elevation_m': None,'status': 'vertical_datum_unresolved'})
    old={'event_id': protocol['event_id'],'grid_cells': 64,'mass_gate_passed': True,'samples': samples,
        'gauge_only_baseline': {'peak_navd88_m': 2.3}}
    new=copy.deepcopy(old);new['grid_cells']=128
    for s in new['samples'][:3]:s.update(error_m=.05,predicted_elevation_m=2.05)
    lost=new['samples'][3];lost['status']='building_cell_unresolved'
    del lost['error_m'];del lost['predicted_elevation_m']
    (tmp_path/'accuracy.json').write_text(json.dumps({'protocol_sha256': digest,'runs': [old,new]}))
    subprocess.run([sys.executable,'-m','scripts.assess_new_event_holdout',str(tmp_path)],cwd=repo,check=True,capture_output=True,text=True)
    scored=json.loads((tmp_path/'holdout-comparison.json').read_text())
    assert scored['regression']['lost_supported_ids']==[16723]
    assert not scored['regression']['regression_gate_passed']
    assert scored['quality_and_spatial_strata'][1]['good_or_excellent']['rmse_m'] is None
    assert scored['quality_and_spatial_strata'][1]['all']['unresolved_ids']==[16723,16666]
    assert not scored['general_flood_accuracy_validated']
    subprocess.run([sys.executable,'scripts/render_new_event_report.py',str(tmp_path)],cwd=repo,check=True,capture_output=True,text=True)
    report=(tmp_path/'holdout-report.html').read_text(encoding='utf-8')
    assert 'Refinement fails' in report and 'vertical_datum_unresolved' in report
    assert 'Good/excellent-quality comparable marks: 0; RMSE Unavailable' in report
