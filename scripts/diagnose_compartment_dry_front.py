"""Post-comparison diagnosis: arrival threshold can conceal false shallow wetting."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT=Path('artifacts/validation/compartment-flow-v1')
coarse=json.loads((ROOT/'dry_start-east.json').read_text())
refined=json.loads((ROOT/'reference-refinement/dry_start.json').read_text())
t=np.asarray(coarse['times_s']);candidate=np.asarray(coarse['traces']['candidate'])[:,-1]
reference=np.asarray(refined['refined_traces'])[:,-1]
rows=[]
for threshold in (1e-5,.001,.01):
    wet=candidate>=threshold;truth=reference>=threshold
    def first(mask):
        ids=np.flatnonzero(mask)
        return float(t[ids[0]]) if len(ids) else None
    rows.append({'threshold_m': threshold,'candidate_first_crossing_s': first(wet),
        'reference_first_crossing_s': first(truth),'candidate_only_wet_frames': int(np.sum(wet&~truth)),
        'reference_only_wet_frames': int(np.sum(truth&~wet)),'frames_compared': len(t)})
decision={'status': 'not_admitted_for_historical_or_production_flow',
    'original_declared_gates_passed': True,'reference_resolution_gates_passed': True,
    'additional_diagnosis_declared_after_results': True,
    'reason': 'The 1 cm arrival threshold hides premature shallow downstream wetting relative to both HLL reference resolutions.',
    'downstream_candidate_peak_depth_m': float(candidate.max()),'downstream_refined_peak_depth_m': float(reference.max()),
    'threshold_diagnostics': rows,
    'interpretation': 'Absolute RMSE and a single arrival threshold are insufficient to establish wet/dry front accuracy. The local-inertial approximation and coarse compartment transport need further diagnosis; no cause is isolated by this test alone.',
    'next_requirements': ['Retain this case as a regression with dry/wet support at multiple declared thresholds.',
        'Compare finer compartment grouping and an independent full-momentum treatment before modifying physics.',
        'Require variable bed and sill/connectivity tests before using real Dorian terrain.',
        'Only after candidate admission, complete real-event testing and another untouched-event check.'],
    'production_enabled': False,'general_flood_accuracy_validated': False,
    'source_sha256': {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ('dry_start-east.json','reference-refinement/dry_start.json','protocol.json')}}
(ROOT/'dry-front-diagnosis.json').write_text(json.dumps(decision,indent=2))
print(json.dumps(decision,indent=2))
