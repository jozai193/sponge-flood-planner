"""Post-result resolution diagnosis; does not alter the frozen acceptance gates."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from scripts.run_refined_compartment_benchmark import GAUGES, TIMES, compare, scene
from services.reference.compartment_flow_candidate import CompartmentFlow, build_graph

root = Path('artifacts/validation/refined-compartment-v1')
sources = ['scripts/diagnose_refined_compartment_failure.py',
           'scripts/run_refined_compartment_benchmark.py', 'services/reference/compartment_flow_candidate.py',
           str(root/'wide_short_pulse.json'), str(root/'wet_to_dry.json')]
protocol = {'declared_after_new_case_failure': True, 'cases': [['wide_short_pulse', .5], ['wet_to_dry', 1.]],
                'purpose': 'Separate spatial grouping/resolution effects from remaining equation/boundary differences',
                'source_sha256': {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources}, 'production_enabled': False}
pp = root/'failure-diagnosis-protocol.json'; encoded = json.dumps(protocol, indent=2)
if pp.exists() and pp.read_text() != encoded: raise ValueError('Frozen diagnostic changed')
pp.write_text(encoded)
rows = []
for case, spacing in protocol['cases']:
    original = json.loads((root/f'{case}.json').read_text())
    z, wall, initial, levels = scene(case); repeat = int(1/spacing)
    z, wall, initial = [a.repeat(repeat, 0).repeat(repeat, 1) for a in (z, wall, initial)]
    graph = build_graph(z, wall, 1, spacing, spacing)
    stage = initial[~wall]
    sim = CompartmentFlow(graph, stage, {'west':lambda t, levels=levels:float(np.interp(t, *np.asarray(levels).T)), 'east':lambda t:0.},
                          roughness=.025, dt_max=.05*spacing)
    traces = []; maxmass = 0.
    for t in TIMES:
        sim.advance(float(t)); h = sim.fine_depth()
        traces.append([float(h[r*repeat:(r+1)*repeat, c*repeat:(c+1)*repeat].mean()) for r, c in GAUGES])
        maxmass = max(maxmass, sim.ledger()['relative_residual'])
    rows.append({'case': case, 'candidate_spacing_m': spacing, 'compartments': len(graph.area),
        'gauges': compare(np.asarray(traces), np.asarray(original['traces']['hll_half_m'])),
        'mass_relative_max': maxmass, 'traces': traces})
result = {'status': 'completed', 'runs': rows, 'production_enabled': False,
              'interpretation': 'Same-spacing disagreement can remain from different equations and boundary formulations; this does not isolate one cause.'}
(root/'failure-diagnosis.json').write_text(json.dumps(result, indent=2))
print(json.dumps([{k:v for k,v in row.items() if k!='traces'} for row in rows]))
