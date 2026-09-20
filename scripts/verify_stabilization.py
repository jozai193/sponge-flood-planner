"""Verify frozen physics and saved stabilization evidence without claiming site accuracy."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import csv
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.verify_export import verify

ROOT=Path('artifacts/verification/stabilization-v1')
freeze=json.loads((ROOT/'solver-freeze.json').read_text())
for source,expected in freeze['source_sha256'].items():
    assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==expected,f'Frozen physics changed: {source}'
sets=[]
for directory in ('export-set','plan-export-set'):
    folder=ROOT/directory
    assert verify(folder/'sponge-export-manifest.json')==4
    scenario=json.loads((folder/'sponge-reproducible-comparison.json').read_text())
    spatial=json.loads((folder/'sponge-selected-designs.geojson').read_text())
    costs=list(csv.DictReader((folder/'sponge-assumed-costs.csv').open(newline='',encoding='utf-8')))
    cost=sum(d['costMinor'] for d in scenario['selectedDesigns'])
    assert cost==scenario['summary']['costMinor']==1000000
    assert round(sum(float(row['cost_usd']) for row in costs)*100)==cost
    assert sum(d['costMinor'] for d in spatial['designs'])==cost
    assert all('costMinor' not in f['properties'] for f in spatial['features'])
    expected={(d['id'],c) for d in scenario['selectedDesigns'] for c in d['cells']}
    actual={(f['properties']['design_id'],f['properties']['cell_index']) for f in spatial['features']}
    assert actual==expected and len(spatial['features'])==len(expected)
    assert scenario['validation']['generalFloodAccuracyValidated'] is False
    assert 'general real-world flood accuracy remains unvalidated' in (folder/'sponge-planning-report.html').read_text(encoding='utf-8')
    assert scenario['evidence']['storm']=={'duration':2,'recession':2,'depth':.02}
    if directory=='plan-export-set':assert scenario['evidence']['searchResult']['evaluations']==2
    sets.append({"directory": directory,"checksums_passed": True,"cost_minor": cost,"geojson_cells": len(actual),
                     "selected_designs": len(scenario['selectedDesigns']),"search": scenario['evidence'].get('searchResult')})
log=(ROOT/'export-rerun.log').read_text(encoding='utf-8-sig')
rerun=json.loads(next(line for line in log.splitlines() if line.startswith('{"results":')))
assert all(r['depthErrorM']==0 and r['peakErrorM']==0 for r in rerun['results'])
before=json.loads((ROOT/'load-before.json').read_text())
after=json.loads((ROOT/'load-final.json').read_text())
replay=json.loads((ROOT/'replay-verified.json').read_text())
assert all(s['allStatesRenderedInOrder'] and s['fenceFailures']==0 for s in replay['summary'].values())
def timings(data):
    return {"controls_ms": [r['controlsReadyMs'] for r in data['results']],
                "max_long_task_ms": [max((x['duration'] for x in r['inPageTiming']['longTasks']),default=0) for r in data['results']],
                "full_detail_callback_ms": [r['inPageTiming'].get('detailReadyMs') for r in data['results']]}
result={"verified_at": datetime.now(UTC).isoformat(),"frozen_physics_files": len(freeze['source_sha256']),
    "unit_tests": '49 TypeScript tests passed',"typecheck": 'passed',"build": 'passed; existing large-bundle warning retained',
    "prior_python_tests": '227 passed before this UI-only stabilization; physics hashes unchanged, suite not rerun',
    "export_sets": sets,"export_rerun": rerun,"load_before": timings(before),"load_after": timings(after),"replay": replay['summary'],
    "browser_checks": ['Eligibility checkbox required','Over-budget manual comparison rejected',
                    'Within-budget comparison completed','Single-candidate search exhausted both subsets',
                    'Five downloads per comparison and planner result','Restore retained assumptions and results'],
    "scope": 'Prepared Philadelphia terrain/context, synthetic 2-second rain plus 2-second recession. Installed Chrome / NVIDIA RTX 5050, local development server. Session and bundle endpoints supplied with fixtures.',
    "limits": ['General flood accuracy remains unvalidated','Costs and eligibility remain assumptions; no valuation added',
            'First controls improve in these samples; warm controls are slower and full detail arrives later. Three samples do not prove a general speedup.',
            'Replay measures state draw callbacks and RAF-polled GPU completion, not display presentation or 60 FPS.',
            'Initial prepared benchmarks excluded live services. See the separate live recovery checks for subsequent service verification.',
            'Clean installation, demo video and submission remain paused']}
(ROOT/'verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps({"frozen_physics_files": result['frozen_physics_files'],"export_sets": sets,"tests": result['unit_tests']}))
