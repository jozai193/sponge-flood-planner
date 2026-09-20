"""Freeze then test selective refinement against old and new synthetic fronts."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from scripts.run_compartment_flow_benchmark import forcing, geometry
from services.api.contracts import SolverConfig
from services.reference.coastal import CoastalBoundary
from services.reference.coastal_segments import CoastalSegments
from services.reference.compartment_flow_candidate import CompartmentFlow, build_graph
from services.reference.refined_compartment_candidate import build_refined_graph
from services.reference.solver_segments_candidate import Solver, Surface

ROOT = Path('artifacts/validation/refined-compartment-v1')
TIMES = np.arange(121.)
GAUGES = [(4, 8), (4, 28), (4, 52)]
THRESHOLDS = [1e-5, .001, .01]


def scene(case):
    z, wall = geometry('dry_start')
    h = np.zeros_like(z)
    if case == 'regression':
        levels = forcing('dry_start')
    elif case == 'wet_to_dry':
        h[4:6, :20] = .1
        levels = ((0., .1), (20., .18), (60., .1), (120., .1))
    elif case == 'wide_short_pulse':
        wall[4:8, :] = False
        wall[5:7, 24:28] = True  # island; two open paths, no point carving
        levels = ((0., 0.), (5., .07), (15., .07), (30., 0.), (120., 0.))
    else:
        raise ValueError(case)
    return z, wall, h, levels


def numerical_reference(z, wall, h, levels, spacing):
    repeat = int(1/spacing)
    zz, ww, hh = [a.repeat(repeat, 0).repeat(repeat, 1) for a in (z, wall, h)]
    ny, nx = zz.shape
    west = tuple(r*nx for r in range(ny) if not ww[r, 0])
    east = tuple(r*nx+nx-1 for r in range(ny) if not ww[r, -1])
    boundaries = CoastalSegments((
        ('upstream', CoastalBoundary('west', west, levels, 'local metres', 'Frozen synthetic forcing')),
        ('downstream', CoastalBoundary('east', east, ((0., 0.),), 'local metres', 'Dry outlet'))))
    return Solver(Surface(zz, spacing, spacing, solid=ww, roughness=.025),
                  SolverConfig(spatial_order=2, dt_max_s=.05*spacing), depth=hh, coastal=boundaries)


def compare(candidate, reference):
    metrics = []
    for k in range(len(GAUGES)):
        a, b = candidate[:, k], reference[:, k]
        threshold_rows = []
        for threshold in THRESHOLDS:
            ai, bi = np.flatnonzero(a >= threshold), np.flatnonzero(b >= threshold)
            ac = int(ai[0]) if len(ai) else None
            bc = int(bi[0]) if len(bi) else None
            threshold_rows.append({"threshold_m": threshold, "candidate_arrival_s": ac,
                "reference_arrival_s": bc, "arrival_error_s": abs(ac-bc) if ac is not None and bc is not None else None,
                "both_never_wet": ac is None and bc is None,
                "candidate_only_wet_frames": int(np.sum((a >= threshold) & (b < threshold))),
                "reference_only_wet_frames": int(np.sum((b >= threshold) & (a < threshold)))})
        metrics.append({"gauge": k, "rmse_m": float(np.sqrt(np.mean((a-b)**2))),
                            "peak_error_m": float(a.max()-b.max()), "thresholds": threshold_rows})
    return metrics


def main():
    ROOT.mkdir(exist_ok=True)
    sources = ['scripts/run_refined_compartment_benchmark.py',
               'services/reference/refined_compartment_candidate.py',
               'services/reference/compartment_flow_candidate.py',
               'services/reference/solver_segments_candidate.py', 'services/reference/solver.py',
               'services/reference/coastal.py', 'services/reference/coastal_segments.py',
               'services/api/contracts.py', 'scripts/run_compartment_flow_benchmark.py',
               'artifacts/validation/compartment-flow-v1/reference-refinement/dry_start.json']
    protocol = {"scope": 'Static selective refinement diagnostic; not observed flood validation',
        "cases": ['regression', 'wet_to_dry', 'wide_short_pulse'],
        "new_cases_declared_before_comparison": ['wet_to_dry', 'wide_short_pulse'],
        "refinement": 'Initially dry blocks at 1e-6 m plus one neighboring block; fixed for entire run',
        "coarse_grouping": 4, "fine_spacing_m": 1., "reference_spacing_m": [1., .5], "roughness": .025,
        "candidate_dt_max_s": .05, "gauges": GAUGES, "duration_s": 120, "thresholds_m": THRESHOLDS,
        "forcing": {c:scene(c)[3] for c in ('regression', 'wet_to_dry', 'wide_short_pulse')},
        "gates": {"candidate_gauge_rmse_max_m": .02, "reference_change_rmse_max_m": .01,
                   "candidate_arrival_error_max_s": 5, "arrival_gate_thresholds_m": [.001, .01],
                   "mass_relative_max": 1e-10, "regression_downstream_max_m": .001},
        "arrival_gate": 'At each gauge and threshold, both never wet or both arrive within 5 seconds; one absent is failure.',
        "spatial_extent": 'Save full depth fields and report wet/dry disagreement, with no post-result acceptance threshold.',
        "limitations": ['Static refinement cannot follow later drying of initially wet coarse blocks.',
                     'All-dry scenes resolve every open pixel; no coarse-grid performance benefit there.',
                     'Local-inertial equations still omit advective momentum; flat beds and permanent walls only.'],
        "research_context": [{'title':'GeoClaw wet/dry and adaptive refinement', 'url':'https://www.clawpack.org/geoclaw.html',
                           'use':'Design context only; no GeoClaw code copied and this is not dynamic AMR.'}],
        "source_sha256": {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},
        "production_enabled": False}
    pp = ROOT/'protocol.json'; encoded = json.dumps(protocol, indent=2)
    if pp.exists() and pp.read_text() != encoded:
        raise ValueError('Frozen protocol changed')
    pp.write_text(encoded)
    rows = []
    for case in protocol['cases']:
        out = ROOT/f'{case}.json'
        if out.exists():
            rows.append(json.loads(out.read_text())['result']); continue
        z, wall, initial, levels = scene(case)
        graph, stage = build_refined_graph(z, wall, 4, initial)
        boundaries = {'west': lambda t, levels=levels:float(np.interp(t, *np.asarray(levels).T)), 'east':lambda t:0.}
        candidate = CompartmentFlow(graph, stage, boundaries, roughness=.025, dt_max=.05)
        coarse_graph = build_graph(z, wall, 4)
        coarse_stage = np.array([initial[coarse_graph.labels == i].mean() for i in range(len(coarse_graph.area))])
        sims = {'selective':candidate, 'coarse':CompartmentFlow(coarse_graph, coarse_stage, boundaries)}
        if case != 'regression':
            sims.update({'hll_1m':numerical_reference(z, wall, initial, levels, 1.),
                         'hll_half_m':numerical_reference(z, wall, initial, levels, .5)})
        traces = {name:[] for name in sims}; fields = {name:[] for name in sims}
        maxmass = {name:0. for name in sims}; elapsed = {name:0. for name in sims}
        for t in TIMES:
            for name, sim in sims.items():
                start = time.perf_counter(); sim.advance(float(t)); elapsed[name] += time.perf_counter()-start
                if name.startswith('hll'):
                    depth = sim.u[..., 0].copy()
                    if name == 'hll_half_m': depth = depth.reshape(16, 2, 64, 2).mean(axis=(1, 3))
                else: depth = sim.fine_depth()
                assert np.isfinite(depth).all() and np.min(depth) >= 0
                traces[name].append([float(depth[r, c]) for r, c in GAUGES]); fields[name].append(depth)
                maxmass[name] = max(maxmass[name], sim.ledger()['relative_residual'])
            if t % 30 == 0: print(json.dumps({'case':case, 'seconds_simulated':t}), flush=True)
        if case == 'regression':
            traces['hll_half_m'] = json.loads(Path(sources[-1]).read_text())['refined_traces']
        values = {name:np.asarray(trace) for name, trace in traces.items()}
        metrics = compare(values['selective'], values['hll_half_m'])
        arrival_pass = all(item['both_never_wet'] or (item['arrival_error_s'] is not None and item['arrival_error_s'] <= 5)
                           for gauge in metrics for item in gauge['thresholds'] if item['threshold_m'] >= .001)
        reference_change = np.sqrt(np.mean((values['hll_1m']-values['hll_half_m'])**2, axis=0)).tolist() if case != 'regression' else None
        gates = {"stage": all(m['rmse_m'] <= .02 for m in metrics), "arrival": arrival_pass,
                     "mass": max(maxmass.values()) <= 1e-10,
                     "reference_resolution": reference_change is None or max(reference_change) <= .01,
                     "regression_dry_support": case != 'regression' or float(values['selective'][:, -1].max()) <= .001}
        extent = []
        if case != 'regression':
            a, b = np.asarray(fields['selective']), np.asarray(fields['hll_half_m'])
            for threshold in THRESHOLDS:
                aw, bw = a[:, ~wall] >= threshold, b[:, ~wall] >= threshold
                union = int(np.sum(aw | bw)); intersection = int(np.sum(aw & bw))
                extent.append({"threshold_m": threshold, "space_time_iou": intersection/union if union else 1.,
                    "candidate_only_wet_cell_frames": int(np.sum(aw & ~bw)), "reference_only_wet_cell_frames": int(np.sum(bw & ~aw))})
        row = {"case": case, "gauges": metrics, "coarse_gauges": compare(values['coarse'], values['hll_half_m']),
                   "reference_change_rmse_m": reference_change, "gates": gates, "all_gates_passed": all(gates.values()),
                   "compartments": len(graph.area), "coarse_compartments": len(coarse_graph.area), "fine_open_cells": int(np.sum(~wall)),
                   "measured_solver_seconds": elapsed, "mass_relative_max": maxmass, "extent_diagnostics": extent,
                   "ledgers": {name:sim.ledger() for name, sim in sims.items()}}
        np.savez_compressed(ROOT/f'{case}-fields.npz', times_s=TIMES, solid=wall, **{name:np.asarray(f) for name, f in fields.items()})
        out.write_text(json.dumps({"times_s": TIMES.tolist(), "traces": traces, "result": row}, indent=2))
        rows.append(row); print(json.dumps({'case':case, 'gates':gates, 'compartments':len(graph.area)}), flush=True)
    (ROOT/'results.json').write_text(json.dumps({"status": 'completed', "runs": rows,
        "candidate_gates_passed": all(r['all_gates_passed'] for r in rows), "production_enabled": False,
        "general_flood_accuracy_validated": False}, indent=2))


if __name__ == '__main__': main()
