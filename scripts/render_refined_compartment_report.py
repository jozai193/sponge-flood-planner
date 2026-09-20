"""Render synthetic refinement evidence without treating it as real flood truth."""
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path('.runtime/validation-plot-libs').resolve()))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from scripts.run_refined_compartment_benchmark import scene
from services.reference.refined_compartment_candidate import build_refined_graph

root = Path('artifacts/validation/refined-compartment-v1')
results = json.loads((root/'results.json').read_text())
fig, axes = plt.subplots(3, 4, figsize=(17, 10), constrained_layout=True)
table = []
arrivals = []
for row, run in enumerate(results['runs']):
    name = run['case']; data = json.loads((root/f'{name}.json').read_text())
    z, wall, initial, levels = scene(name)
    graph, _ = build_refined_graph(z, wall, 4, initial)
    areas = np.where(graph.labels >= 0, graph.area[np.maximum(graph.labels, 0)], np.nan)
    axes[row, 0].imshow(areas, origin='lower', extent=[0, 64, 0, 16], vmin=1, vmax=8, cmap='viridis')
    axes[row, 0].set_title(name.replace('_', ' ')+'\nCell area: dark = 1 m², bright = 8 m²')
    axes[row, 0].set_xlabel('Distance (m)'); axes[row, 0].set_ylabel('Distance (m)')
    for k in range(3):
        ax = axes[row, k+1]
        for key, label, color in [('hll_half_m', '0.5 m HLL', '#111111'), ('coarse', '4 m groups', '#c6402e'),
                                   ('selective', 'Selective refinement', '#087d68')]:
            values = np.asarray(data['traces'][key])
            ax.plot(data['times_s'], values[:, k]*1000, label=label, color=color, linewidth=1.4)
        ax.set_title(f'Gauge {k+1}'); ax.set_xlabel('Seconds'); ax.set_ylabel('Depth (mm)'); ax.grid(alpha=.2)
        if row == 0 and k == 0: ax.legend(fontsize=8)
    errors = [g['rmse_m']*1000 for g in run['gauges']]
    old_errors = [g['rmse_m']*1000 for g in run['coarse_gauges']]
    bad = ', '.join(k for k, v in run['gates'].items() if not v) or 'none'
    table.append(f'<tr><td>{html.escape(name)}</td><td>{run["compartments"]} / {run["fine_open_cells"]}</td>'
                 f'<td>{", ".join(f"{v:.2f}" for v in errors)}</td>'
                 f'<td>{", ".join(f"{v:.2f}" for v in old_errors)}</td><td>{bad}</td></tr>')
    for gauge in run['gauges']:
        for item in gauge['thresholds']:
            if item['threshold_m'] < .001: continue
            def arrival(v): return 'Never reached' if v is None else f'{v} s'
            arrivals.append(f'<tr><td>{name}</td><td>{gauge["gauge"]+1}</td><td>{item["threshold_m"]*1000:g} mm</td>'
                f'<td>{arrival(item["candidate_arrival_s"])}</td><td>{arrival(item["reference_arrival_s"])}</td>'
                f'<td>{item["candidate_only_wet_frames"]} / {item["reference_only_wet_frames"]}</td></tr>')
fig.savefig(root/'comparison.png', dpi=150); plt.close(fig)
allpass = results['candidate_gates_passed']
decision = 'Synthetic gates passed; historical admission still withheld' if allpass else 'New synthetic comparisons reject historical admission'
payload = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Selective refinement diagnostic</title><style>
body{{font:16px/1.6 system-ui;background:#edf2f1;color:#172b2a;margin:0}}main{{max-width:1250px;margin:auto;padding:32px}}
h1{{line-height:1.15;font-size:36px}}h2{{margin-top:32px}}.notice{{padding:20px;background:#fff1d5;border-left:5px solid #ab6800}}
img{{width:100%;background:white}}table{{border-collapse:collapse;width:100%;background:white;font-size:14px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #dce4e2}}
a{{color:#006d61}}.scroll{{overflow:auto}}</style><main>
<p><a href="../index.html">Validation dashboard</a> / experimental numerical work</p>
<h1>Smaller cells at the wetting front</h1><div class="notice"><strong>{decision}.</strong>
 Production remains unchanged. These references are numerical simulations, not observations of an actual flood.</div>
<p>This candidate splits initially dry 4 m blocks into 1 m cells, plus a one-block buffer. Established wet areas can stay coarse.
The spatial layout stays fixed throughout the run. The underlying local-inertial momentum equations are unchanged.</p>
<p>The original dry-start discrepancy is a regression case. Two additional synthetic cases were fixed before their results were inspected:
a wet reservoir advancing onto dry ground, and a wider channel with an island and a shorter pulse. No result-dependent parameter changes were made.</p>
<h2>Results against the 0.5 m HLL reference</h2><div class="scroll"><table><tr><th>Case</th><th>Candidate / fully fine cells</th>
<th>Selective RMSE (mm), upstream to downstream</th><th>Coarse RMSE (mm)</th><th>Failed declared gates</th></tr>{''.join(table)}</table></div>
<p><strong>Passing absolute limits does not establish consistent improvement.</strong> In the wet-to-dry case,
selective refinement worsens the middle and downstream gauge RMSE relative to the coarse candidate.
That cross-case regression is retained; this is not a production recommendation.</p>
<p>In the island-channel case, the 1 mm front reaches the middle gauge at 80 s versus 117 s in the 0.5 m HLL reference,
failing the frozen 5 s arrival limit. The 1 m HLL reference arrives at 112 s.</p>
<p>Gates require mass error below 1e-10, gauge RMSE at most 20 mm, and matching 1 mm and 10 mm arrivals within 5 seconds.
At a given threshold, one model arriving while the other never arrives is a failure. The 0.01 mm threshold remains visible in raw diagnostics.</p>
<img src="comparison.png" alt="Three synthetic geometries and gauge depth comparisons between coarse, selectively refined and HLL models">
<h2>Arrival and dry/wet disagreement</h2><div class="scroll"><table><tr><th>Case</th><th>Gauge</th><th>Threshold</th>
<th>Selective arrival</th><th>Reference arrival</th><th>Only selective / only reference wet frames</th></tr>{''.join(arrivals)}</table></div>
<p>Each frame represents one second. Full-field depth arrays and space-time intersection-over-union are retained for both new cases.
No acceptance cutoff was fitted to those extent results.</p>
<h2>Cost and limits</h2><p>All-dry scenes resolve every open pixel, so they lose the intended coarse-cell saving.
Static refinement cannot follow a later dry front into an initially wet coarse area. Bed sills, changing terrain, advective momentum,
and a physically admitted historical boundary still need work. Passing a software test is not proof of flood accuracy.</p>
<h2>Diagnosis after the failure</h2><p>A separate run refined the local-inertial candidate to 0.5 m, matching HLL spacing.
The middle-gauge 1 mm arrival moved to 88 s, still 29 s earlier than HLL. Finer cells help but do not resolve the discrepancy.
Different momentum equations and boundary formulations remain possible causes; this test does not isolate either one.</p>
<p>The next controlled comparison should align boundary fluxes and compare full-momentum transport before historical testing.
No Dorian sensor values were needed or inspected for these synthetic tests.</p>
<p>Refinement design context: <a href="https://www.clawpack.org/geoclaw.html">GeoClaw documentation</a>.
GeoClaw uses adaptive refinement and wet/dry solvers; this experiment is a simpler static local implementation, with no copied GeoClaw code.</p>
<p><a href="protocol.json">Frozen protocol and source hashes</a> · <a href="results.json">All metrics</a> ·
<a href="failure-diagnosis.json">Same-resolution diagnosis</a> ·
<a href="../compartment-flow-v1/report.html">Previous coarse-cell failure</a></p></main></html>'''
(root/'report.html').write_text(payload, encoding='utf-8')
print(decision)
