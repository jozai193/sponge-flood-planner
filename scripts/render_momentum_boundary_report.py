"""Explain controlled mechanism comparisons with their attribution limits."""
import html
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path('artifacts/validation/momentum-boundary-v1')
result=json.loads((root/'results.json').read_text())
cases=['open_island','closed_island','closed_straight']
names={'hll_full':'Full momentum HLL','hll_no_advection':'HLL without advection','graph_local_inertial':'Graph local inertial'}
colors={'hll_full':'#151d25','hll_no_advection':'#3657ae','graph_local_inertial':'#c94b31'}
fig,axes=plt.subplots(3,3,figsize=(15,11),layout='constrained')
rows=[];exchange=[];failure=[]
for i,case in enumerate(cases):
    for kind,label in names.items():
        data=json.loads((root/f'{case}-{kind}.json').read_text());run=data['result']
        if not run['numerical_gates_passed']:failure.append(f'{case} / {kind}: {run["error"] or "numerical gate failure"}')
        a=np.asarray(data['traces'])
        for j,k in enumerate((0,1,2)):
            axes[i,j].plot(data['times_s'],a[:,k]*1000,label=label,color=colors[kind])
            axes[i,j].set_title(f'{case.replace("_"," ")} / gauge {k+1}')
            axes[i,j].set_xlabel('Time (s)');axes[i,j].set_ylabel('Depth (mm)');axes[i,j].grid(alpha=.2)
        ledger=run['ledger']
        exchange.append(f'<tr><td>{case}</td><td>{label}</td><td>{ledger["inflow_m3"]:.6f}</td>'
            f'<td>{ledger["outflow_m3"]:.6f}</td><td>{run["mass_relative_max"]:.2e}</td></tr>')
    axes[i,0].legend(fontsize=8)
for comparison in result['comparisons']:
    if not comparison['eligible']:continue
    for gauge in comparison['gauges']:
        if gauge['gauge']!=2:continue
        t=next(x for x in gauge['thresholds'] if x['threshold_m']==.001)
        show=lambda v:'Not reached' if v is None else str(v)
        rows.append(f'<tr><td>{comparison["case"]}</td><td>{names[comparison["model"]]}</td>'
            f'<td>{show(t["candidate_arrival_s"])}</td><td>{show(t["full_hll_arrival_s"])}</td>'
            f'<td>{show(t["signed_arrival_difference_s"])}</td><td>{gauge["rmse_m"]*1000:.3f}</td></tr>')
fig.savefig(root/'comparison.png',dpi=140);plt.close(fig)
diagnosis=json.loads((root/'diagnosis.json').read_text()) if (root/'diagnosis.json').exists() else None
findings=''.join(f'<li>{html.escape(x)}</li>' for x in diagnosis['findings']) if diagnosis else '<li>See frozen numerical comparisons below.</li>'
page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Momentum and boundary diagnosis</title><style>body{{background:#eef3f3;color:#20302f;font:16px/1.65 system-ui;margin:0}}
main{{max-width:1200px;margin:auto;padding:32px}}h1{{font-size:36px;line-height:1.15}}h2{{margin-top:32px}}
.notice{{background:#fff1d4;border-left:5px solid #a86600;padding:20px}}img{{width:100%}}table{{border-collapse:collapse;width:100%;background:white;font-size:14px}}
th,td{{padding:9px;text-align:left;border-bottom:1px solid #dde4e3}}a{{color:#006b60}}.scroll{{overflow:auto}}</style>
<main><p><a href="../index.html">Validation dashboard</a> / mechanism diagnosis</p><h1>Why does the simplified flow arrive too early?</h1>
<div class="notice">Controlled numerical diagnosis only. Production is unchanged. These are not observed flood comparisons.</div>
<ul>{findings}</ul><h2>What was held constant?</h2>
<p>All models use the same 1 m terrain, permanent walls, initial water, roughness, output times and maximum timestep.
Both HLL variants share reconstruction, integration, source and wall treatment. The ablation removes momentum advection and uses the wave speeds of that reduced equation.</p>
<p>The open island case uses the original prescribed water-level pulse. Two new closed cases release the same finite volume of water,
with and without an island. Closed cases have no external water exchange, removing ocean-boundary forcing as an explanation there.</p>
<h2>Arrival at gauge 3, just beyond the island position</h2><p>Arrival threshold: 1 mm. Signed difference is candidate minus full HLL; negative means early.
RMSE covers all 181 frames. Every other gauge and threshold is retained in <a href="results.json">the results</a>.</p>
<div class="scroll"><table><tr><th>Case</th><th>Variant</th><th>Arrival (s)</th><th>Full HLL (s)</th><th>Difference (s)</th><th>RMSE (mm)</th></tr>{''.join(rows)}</table></div>
<img src="comparison.png" alt="Open and closed case traces for full momentum, reduced momentum HLL and graph local inertial flow">
<h2>Water exchange and conservation</h2><div class="scroll"><table><tr><th>Case</th><th>Model</th><th>Inflow (m³)</th><th>Outflow (m³)</th><th>Maximum relative mass residual</th></tr>{''.join(exchange)}</table></div>
<h2>What this can and cannot establish</h2><p>Equal ghost-state construction does not force equal open-boundary fluxes. Open runs retain their separate inflow/outflow ledgers.
Closed tests can show that an external boundary difference is not necessary for a discrepancy, but cannot assign a percentage of the original open-case error to it.</p>
<p>Graph versus HLL also changes momentum staggering, numerical diffusion and friction discretization. Removing HLL advection changes both physical momentum flux
and its characteristic speeds. This is a controlled equation comparison, not a claim that one code line explains all errors. The 1 m suite is not a convergence proof.</p>
<p>Literature context: <a href="https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1002/wrcr.20366">de Almeida and Bates (2013)</a>
describes the local-inertial approximation and its applicability limits. Its omission of convective acceleration motivates this diagnostic; no published accuracy number is transferred to our model.</p>
<p><a href="protocol.json">Frozen protocol</a> · <a href="diagnosis.json">Decision record</a> · <a href="verification.json">Verification</a> ·
<a href="../refined-compartment-v1/report.html">Prior refinement failure</a></p>
{('<p>Numerical failures: '+html.escape('; '.join(failure))+'</p>') if failure else ''}</main></html>'''
(root/'report.html').write_text(page,encoding='utf-8')
print('Rendered momentum and boundary diagnostic')
