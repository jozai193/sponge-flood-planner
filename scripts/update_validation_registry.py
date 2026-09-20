"""Record verified experimental milestones without rewriting historical protocols."""
import hashlib
import json
from pathlib import Path

root=Path('artifacts/validation');path=root/'experiment-registry.json'
registry=json.loads(path.read_text())
michael=next(e for e in registry['events'] if e['id']=='michael-2018')
michael.update(role='independent_source_comparison',
    observations_exposed=True,
    exposure_note='A published source preview exposed one nearby HWM elevation. Raw STN outcomes are downloaded; forcing and parameters were frozen before local scoring. This event is not strictly blinded.',
    protocol='michael-2018/protocol.json',
    status='completed' if (root/'michael-2018/accuracy.json').exists() else 'frozen_simulation_running',
    terrain_note='2017 lidar did not cover the original bay domain. Uses sourced NOAA 2010 integrated land/seabed elevations, with old-survey limitations.')
if (root/'michael-2018/accuracy.json').exists():
    audit=json.loads((root/'michael-2018/accuracy.json').read_text())
    michael.update(baseline='baselines/michael-initial/manifest.json',
        supported_comparisons=sum(r['compared_count'] for r in audit['runs']),
        outcome='Numerical run complete; both retained marks originated in buildings and are unsupported. No accepted real-event RMSE. Preliminary indoor-misclassified score withdrawn.',
        diagnosis='michael-2018/point-diagnosis.json')
registry['final_holdout']={'status': 'screened_out_local_observations_unavailable','event_id': 'USGS-STN-304-2020-Sally',
    'city': 'Pensacola','observations_exposed': False,
    'terrain_candidate': 'NOAA regional/pensacola_13_navd88_2015.nc (catalog entry confirmed)',
    'requirements': 'Current STN event endpoint returned one Louisiana mark, none near Pensacola. Measured elevations not inspected. Other sources may exist; no simulation run.'}
for name in ('ian-2022','irma-2017','matthew-2016'):
    folder=root/name
    if not (folder/'protocol.json').exists():continue
    protocol=json.loads((folder/'protocol.json').read_text())
    completed=(folder/'accuracy.json').exists()
    entry={'id': name,'city': protocol['city'],'role': 'metadata_reviewed_independent_event_screening',
        'observations_exposed': completed,'protocol': name+'/protocol.json',
        'status': 'completed' if completed else 'frozen_simulation_running',
        'exposure_note': 'Coordinates and numeric-redacted descriptions reviewed before freezing; measured HWM elevations not inspected before simulation.',
        'terrain_note': protocol['terrain_acquisition'],'review': name+'/observation-review.json'}
    if completed:
        a=json.loads((folder/'accuracy.json').read_text())['runs'][-1]
        entry.update(compared_count=a['compared_count'],dry_misses=a['missed_flood_count'],rmse_m=a['rmse_m'],mass_gate_passed=a['mass_gate_passed'])
    holdout=folder/'holdout-comparison.json'
    if holdout.exists():
        comparison=json.loads(holdout.read_text())
        entry.update(role='held_out_until_scoring_now_development_evidence',
            holdout_decision=comparison['decision'],
            general_flood_accuracy_validated=False,
            next_change_requires_another_untouched_event=True)
        registry['latest_completed_holdout']={'event_id': name,'decision': comparison['decision'],
            'result': name+'/holdout-comparison.json','observations_exposed': True,
            'reuse': 'Retained regression and diagnosis; no longer an untouched test for changes informed by these results.'}
    registry['events']=[e for e in registry['events'] if e['id']!=name]+[entry]
registry['resolution_candidates']=[]
flow=root/'compartment-flow-v1/results.json'
if flow.exists():
    candidate=json.loads(flow.read_text())
    registry['compartment_flow_candidate']={'status': candidate['status'],
        'candidate_gate_passed': candidate['candidate_gate_passed'],
        'report': 'compartment-flow-v1/report.html','production_enabled': False,
        'scope': 'Synthetic flat-bed channels, permanent walls, isolated pools and dry starts; no general terrain support'}
    refined=root/'compartment-flow-v1/reference-refinement/results.json'
    if refined.exists():
        registry['compartment_flow_candidate']['reference_refinement_passed']=json.loads(refined.read_text())['reference_gates_passed']
    diagnosis=root/'compartment-flow-v1/dry-front-diagnosis.json'
    if diagnosis.exists():
        registry['compartment_flow_candidate'].update(adoption_decision=json.loads(diagnosis.read_text())['status'],
            diagnostic='compartment-flow-v1/dry-front-diagnosis.json',
            limitation='Coarse grouping causes premature shallow wetting hidden by the original arrival threshold; general bed variation unsupported.')
selective=root/'refined-compartment-v1/results.json'
if selective.exists():
    result=json.loads(selective.read_text())
    registry['selective_refinement_candidate']={'status': result['status'],
        'numerical_gates_passed': result['candidate_gates_passed'],
        'report': 'refined-compartment-v1/report.html','production_enabled': False,
        'adoption_decision': 'withheld_failed_new_case_arrival_and_mixed_case_rmse_regression',
        'scope': 'Static dry-region refinement; three synthetic cases, not observed flood validation'}
momentum=root/'momentum-boundary-v1/diagnosis.json'
if momentum.exists():
    registry['momentum_boundary_diagnosis']={'status': 'completed_mechanism_diagnosis',
        'report': 'momentum-boundary-v1/report.html','production_enabled': False,
        'conclusion': 'Removing HLL advection does not reproduce graph early arrival; boundary exchange replay failed matching, closed controls remain valid.',
        'recommendation': 'Retain production full-momentum HLL; experimental graph remains withheld'}
regional=root/'dorian-2019/cora-forcing-candidate-v1/results.json'
if regional.exists():
    forcing=json.loads(regional.read_text())
    registry['cora_forcing_candidate']={'status': forcing['status'],
        'fully_valid_perimeter_points': forcing['perimeter_points_valid_entire_period'],
        'total_perimeter_points': len(forcing['points']),'datum_offset_applied': None,
        'production_enabled': False,'source_kind': 'Regional model output, not observed flood truth'}
wave=root/'wave-boundary-v1/results.json'
if wave.exists():
    wr=json.loads(wave.read_text())
    registry['wave_boundary_candidate']={'status': wr['status'],
        'report': 'wave-boundary-v1/report.html','numerical_gate_passed': wr['numerical_gate_passed'],
        'production_enabled': False,'general_flood_accuracy_validated': False,
        'forcing_limit': 'Incoming wave about a still background, not a measured total gauge stage.'}
if (root/'dorian-2019/sensor-review.json').exists():
    registry['dorian_sensor_screen']={'report': 'dorian-2019/sensor-review.html',
        'status': 'metadata_only_two_site_candidate','observations_exposed': False,
        'limitation': 'Sensor datum, QC, channel geometry and boundary forcing remain to be verified.'}
if (root/'dorian-2019/sensor-input-audit.json').exists():
    sensor_audit=json.loads((root/'dorian-2019/sensor-input-audit.json').read_text())
    registry['dorian_sensor_screen'].update(report='dorian-2019/input-audit.html',
        status=sensor_audit['status'],checks=sensor_audit['checks'],
        limitation='NetCDF datum/units/time verified. Ferry coordinates conflict; creek is poorly represented in coarse terrain; independent ocean/sound forcing unresolved.')
lab=root/'okushiri-lab/results.json'
if lab.exists():
    lab_result=json.loads(lab.read_text())
    registry['laboratory_benchmark']={'status': lab_result['status'],
        'report': 'okushiri-lab/report.html','results': 'okushiri-lab/results.json',
        'production_enabled': False,'general_flood_accuracy_validated': False,
        'scope': 'Published physical laboratory gauges at two fixed resolutions; original and isolated CPU boundary-segment candidate.'}
source_audit=root/'free-data-workflow/source-audit.json'
if source_audit.exists():
    audit=json.loads(source_audit.read_text())
    registry['free_data_workflow']={'status': audit['status'],
        'report': 'free-data-workflow/index.html','audit': 'free-data-workflow/source-audit.json',
        'eligible_area_references': sum(s['area_score_admission']['eligible_for_precision_iou'] for s in audit['sources']),
        'general_flood_accuracy_validated': False}
domain=root/'matthew-2016-domain4km'
if (domain/'protocol.json').exists():
    job=json.loads((domain/'job-status.json').read_text()) if (domain/'job-status.json').exists() else {'stage':'queued'}
    registry['domain_experiment']={'directory': domain.name,'status': job['stage'],
        'scope': 'Exposed Matthew development diagnostic: 4 km versus 2 km at fixed 31.25 m spacing with identical shared bed and mask.','production_enabled': False}
    if (domain/'domain-comparison.json').exists():
        comparison=json.loads((domain/'domain-comparison.json').read_text())
        registry['domain_experiment'].update(decision=comparison['decision'],regression_gate_passed=comparison['regression_gate_passed'])
registry['positivity_candidates']=[]
for name in ('sandy-2012-positivity-v1','matthew-2016-positivity-v1'):
    folder=root/name
    if not (folder/'protocol.json').exists():continue
    job=json.loads((folder/'job-status.json').read_text()) if (folder/'job-status.json').exists() else {'stage':'queued'}
    item={'directory': name,'status': job['stage'],'production_enabled': False}
    if (folder/'candidate-comparison.json').exists():
        result=json.loads((folder/'candidate-comparison.json').read_text())
        item.update(candidate_numerical_regression_passed=result['candidate_numerical_regression_passed'],
            max_saved_depth_difference_m=result['max_saved_depth_difference_m'],
            max_saved_peak_difference_m=result['max_saved_peak_difference_m'])
    registry['positivity_candidates'].append(item)
if (root/'dorian-2019/eligibility-review.json').exists():
    registry['next_unexposed_candidate']={'event': 'dorian-2019','status': 'not_ready_for_multi_site_holdout',
        'observation_values_exposed': False,'review': 'dorian-2019/eligibility-review.json',
        'limitation': 'Boundary representation and building-corner setting need resolution; currently one clearly outdoor mark.'}
if (root/'dorian-2019/exposure-notice.json').exists():
    registry.pop('next_unexposed_candidate',None)
    registry['dorian_sensor_screen'].update(observations_exposed=True,
        sensor_trace_values_read=False,fully_untouched_event=False,
        exposure_record='dorian-2019/exposure-notice.json',
        next_change_requires_another_untouched_event=True,
        regional_boundary_review='dorian-2019/cora-boundary-preflight.html')
    registry['next_diagnostic_candidate']={'event': 'dorian-2019',
        'status': 'partially_exposed_input_diagnosis','report': 'dorian-2019/input-audit.html'}
if (root/'subgrid-storage-v1/results.json').exists():
    storage=json.loads((root/'subgrid-storage-v1/results.json').read_text())
    registry['subgrid_storage_candidate']={'status': storage['status'],
        'geometry_gates_passed': storage['geometry_gates_passed'],
        'scope': 'Potential terrain storage only; not a hydraulic solver or flood validation',
        'report': 'subgrid-storage-v1/report.html','production_enabled': False}
for name in ('irma-2017-grid128','ian-2022-grid128','sandy-2012-grid128'):
    folder=root/name
    if not (folder/'protocol.json').exists():continue
    item={'directory': name,'change': '128-grid from unchanged sources; no physical parameter fitting',
        'status': 'completed' if (folder/'accuracy.json').exists() else 'running',
        'protocol': name+'/protocol.json','production_adopted': False}
    failure=folder/'replay-failure-diagnosis.json'
    if failure.exists() and not json.loads(failure.read_text())['accepted_for_accuracy']:
        item.update(status='replay_rejected',regression_gate_passed=False,
            decision='no_accepted_accuracy_comparison',diagnosis=name+'/replay-failure-diagnosis.json')
    if (folder/'regression-comparison.json').exists():
        comparison=json.loads((folder/'regression-comparison.json').read_text())
        item.update(regression_gate_passed=comparison['regression_gate_passed'],decision=comparison['decision'])
    registry['resolution_candidates'].append(item)
new=[{'id': '002-mapped-extent-diagnostic','status': 'complete','model_change': 'None',
    'finding': 'At 64 cells, 4566.995 m2 within the NYC mapped flood zone remains dry: 3839.374 m2 at or above the supplied gauge peak and 727.621 m2 below peak but disconnected. No mapped dry cells have a below-peak connected path. This is a diagnostic against a HWM/DEM-derived map, not independent extent validation.',
    'artifacts': ['sandy-2012/extent-comparison.json','sandy-2012/connectivity-diagnosis.json']},
    {'id': '003-coastal-float64-reference','status': 'verified','model_change': 'Added tidal-boundary support to the float64 reference solver; production GPU solver unchanged.',
    'evidence': 'Still-water equilibrium and tide rotation/mass checks pass. Four tidal orientations plus an anisotropic partial-boundary case match GPU peak depths within 0.000003 m on NVIDIA and 0.000001 m on SwiftShader. 163 Python contract/numerical tests pass (2026-09-14), including independent depth-volume checks, retained supported-point regressions, unresolved-datum handling, source-date provenance, rejected-replay diagnostics and the held-out scoring/report pipeline.',
    'limitation': 'Verifies implementations of shared assumptions; does not demonstrate real-event skill or resolve intermittent coastal replay discrepancy.',
    'artifacts': ['coastal-reference/float64.json','coastal-reference/nvidia.json','coastal-reference/software.json']},
    {'id': '004-replay-and-comparison-integrity','status': 'verified','model_change': 'Production physics unchanged. Added atomic historical checkpoints, full saved-frame checks and site-balanced regression gates.',
    'evidence': 'An interrupted and resumed 121-frame GPU fixture exactly matches uninterrupted frames, steps and ledger. Both Sandy grids and both recovery outputs pass the saved-frame audit. Regression checks retain dry misses and prevent repeated marks at one site hiding worse errors elsewhere.',
    'artifacts': ['checkpoint-recovery/result.json','replay-integrity-audit.json','sandy-2012/site-balanced-assessment.json']}]
for item in new:
    registry['iterations']=[old for old in registry['iterations'] if old['id']!=item['id']]+[item]
path.write_text(json.dumps(registry,indent=2))
files=[Path(p) for p in ['services/reference/coastal.py','services/reference/solver.py',
    'tests/numerics/test_coastal_reference.py','scripts/prepare_coastal_reference.py','scripts/verify-coastal-reference.mjs']]
files+=list((root/'coastal-reference').glob('*.json'))
(root/'coastal-reference/checksums.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.name!='checksums.json'},indent=2))
print('Registry updated from verified milestones')
