"""Inspect every controlled flow case and retain limitations next to results."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
sys.path.insert(0,str(Path.cwd()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from scripts.run_compartment_flow_benchmark import geometry
from services.reference.compartment_flow_candidate import build_graph

ROOT=Path('artifacts/validation/compartment-flow-v1')
r=json.loads((ROOT/'results.json').read_text())
cases=[x for x in r['runs'] if x['orientation']=='east']
fig,axes=plt.subplots(5,2,figsize=(13,14),layout='constrained',gridspec_kw={'width_ratios':[1,1.2]})
table=''
for ax,row in zip(axes,cases):
    case=row['case'];z,solid=geometry(case);g=build_graph(z,solid,4)
    labels=np.ma.masked_where(solid,g.labels)
    ax[0].imshow(labels,origin='lower',extent=(0,64,0,16),interpolation='nearest',cmap='tab20')
    ax[0].set_facecolor('#363e44');ax[0].set(title=case.replace('_',' '),xlabel='Channel length (m)',ylabel='Width (m)')
    ax[0].set_xticks(np.arange(0,65,4),minor=True);ax[0].set_yticks(np.arange(0,17,4),minor=True);ax[0].grid(which='minor',alpha=.2)
    ax[0].scatter([28.5,52.5],[4.5,4.5],marker='x',c='black',s=45)
    data=json.loads((ROOT/f'{case}-east.json').read_text());t=np.asarray(data['times_s'])
    for k,color,label in ((1,'#007c91','middle'),(2,'#bd5d3d','downstream')):
        for method,style in [('fine_hll','-'),('candidate','--')]:
            v=np.asarray(data['traces'][method])[:,k]
            ax[1].plot(t,v,style,c=color,label=f'{label}: {"fine HLL" if method=="fine_hll" else "candidate"}')
    ax[1].set(xlabel='Time (s)',ylabel='Water depth (m)',title='Water levels at two fixed cells')
    ax[1].grid(alpha=.2);ax[1].legend(fontsize=7,ncol=2)
    maxerror=max(s['rmse_m'] for s in row['scores']);lag=max(s['arrival_error_s'] or 0 for s in row['scores'])
    table+=f"<tr><td>{case.replace('_',' ')}</td><td>{maxerror*1000:.2f}</td><td>{max(abs(s['peak_error_m']) for s in row['scores'])*1000:.2f}</td><td>{lag:.0f}</td><td>{row['downstream_recession_rmse_m']*1000:.2f}</td><td>{row['candidate_max_froude']:.3f}</td><td>{'PASS' if row['all_gates_passed'] else 'FAIL'}</td></tr>"
fig.suptitle('Connected-compartment flow versus fine-grid HLL\nFlat beds and permanent walls only; each coloured region has separate storage',fontsize=15)
fig.savefig(ROOT/'flow-comparison.png',dpi=140);plt.close(fig)
refinement='Reference refinement is running; no completed result inferred.'
path=ROOT/'reference-refinement/results.json'
if path.exists():
    ref=json.loads(path.read_text())
    refinement=f"Half-spacing HLL reference checks: {'PASS' if ref['reference_gates_passed'] else 'FAIL'}. "
    refinement+=' '.join(f"{x['case'].replace('_',' ')}: maximum reference change {1000*max(x['reference_change_rmse_m']):.2f} mm RMSE; candidate versus refined reference {1000*max(x['candidate_vs_refined_rmse_m']):.2f} mm." for x in ref['runs'])
diagnosis=json.loads((ROOT/'dry-front-diagnosis.json').read_text())
grouping=json.loads((ROOT/'grouping-diagnosis/results.json').read_text())
fig,ax=plt.subplots(figsize=(9,4.6),layout='constrained')
refined=json.loads((ROOT/'reference-refinement/dry_start.json').read_text())
t=np.asarray(refined['times_s'])
ax.plot(t,1000*np.asarray(refined['refined_traces'])[:,-1],color='black',lw=2,label='0.5 m full HLL reference')
for run,color in zip(grouping['runs'],('#147363','#dc9a2a','#b84432')):
    ax.plot(t,1000*np.asarray(run['traces'])[:,-1],color=color,label=f"{run['grouping']} m compartment grouping")
ax.axhline(1,color='gray',ls=':',label='1 mm diagnostic threshold')
ax.set(title='Dry-front discrepancy grows with coarse grouping',xlabel='Time (s)',ylabel='Downstream water depth (mm)',xlim=(80,120))
ax.grid(alpha=.2);ax.legend(fontsize=9)
fig.savefig(ROOT/'dry-front-grouping.png',dpi=150);plt.close(fig)
html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Compartment flow experiment</title><style>body{{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42;margin:0}}main{{max-width:1180px;margin:auto;padding:26px}}img{{width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #d3dcd7}}.scroll{{overflow:auto}}.notice{{background:#fff0d7;padding:18px}}a{{color:#006b85}}li{{margin:8px 0}}</style><main>
<h1>Flow tests expose premature wetting at coarse resolution</h1><p class="notice"><strong>Candidate withheld from historical and production use.</strong> The original absolute-error gates passed, but a subsequent wet/dry diagnosis found a failure hidden by the 1 cm arrival threshold. This tests flat-bed channels and fixed impermeable walls; general Dorian terrain remains unsupported.</p>
<p>Each connected region within a 4 m cell gets separate storage. Flow width comes from actual 1 m openings across a cell face, so a disconnected pool does not fill merely because it shares a coarse cell with a channel. The candidate uses local-inertial momentum with Manning friction and a conservative outgoing-volume limit. The numerical reference uses the existing full shallow-water HLL solver at 1 m spacing.</p>
<h2>Five geometries, two orientations, fixed input pulses</h2><p>All ten runs pass the thresholds written before the simulations. Wet cases use a 20 mm boundary pulse over 0.5 m of water. Their maximum RMSE is {1000*max(s['rmse_m'] for x in cases if x['case']!='dry_start' for s in x['scores']):.2f} mm. That is still a material fraction of this small pulse; an absolute-tolerance pass is not perfect wave reproduction. The dry-start case uses a 0.1 m input and approaches critical flow.</p>
<div class="scroll"><table><tr><th>Case</th><th>Max RMSE (mm)</th><th>Max peak error (mm)</th><th>Max arrival error (s)</th><th>Downstream recession RMSE (mm)</th><th>Max candidate Froude</th><th>Gate</th></tr>{table}</table></div>
<p>Identical results after transposing eastward flow to northward flow. Worst relative mass residual: {max(max(x['max_mass_residual'].values()) for x in r['runs']):.2e}. The isolated pool stays exactly dry, and the blocked channel has no downstream level change. Both solvers miss the downstream arrival threshold in the short dry-start case; this is recorded as no threshold crossing, not proof of downstream arrival skill.</p>
<img src="flow-comparison.png" alt="Five synthetic channel geometries and paired reference and candidate water-depth traces">
<h2>Reference-resolution check</h2><p>{refinement}</p><p>This check was declared after the first comparisons, with no changes to the candidate. It refines the same physical walls and averages back to the original sampling cells. It remains a numerical consistency check, not an observed flood test.</p>
<h2>The original arrival threshold concealed a dry-front failure</h2><p>At the downstream dry-start gauge, refined HLL remains dry throughout the 120 s run, while the 4 m candidate reaches {diagnosis['downstream_candidate_peak_depth_m']*1000:.2f} mm. Both stay below 1 cm, so the original arrival check cannot detect this discrepancy. At 1 mm, the candidate reports water for 12 saved frames where the reference is dry.</p>
<img src="dry-front-grouping.png" alt="Premature downstream wetting reduces as compartment grouping is refined from 4 to 2 to 1 metre">
<p>Keeping the same candidate equations and forcing, the downstream maximum drops from 7.49 mm at 4 m grouping to 0.635 mm at 2 m and effectively zero at 1 m. This implicates coarse spatial grouping in the shallow-front error. Upstream errors remain, and this test does not separately isolate momentum approximation and reservoir-boundary effects. Simply refining to 1 m also forfeits the intended coarse-grid advantage.</p>
<p>The next candidate needs a conservative way to delay within-cell wetting until water traverses the channel, plus stage-dependent sill connectivity. Preserve multiple wet/dry thresholds in later comparisons. The original protocol remains unchanged; this later diagnostic is explicit. <a href="dry-front-diagnosis.json">Decision record</a> · <a href="grouping-diagnosis/results.json">Grouping experiment</a>.</p>
<h2>What remains unsupported</h2><ul><li>Internal bed variation is rejected: we still need a model of sills and stage-dependent connectivity.</li><li>Local-inertial momentum omits advective acceleration and turning losses; larger pulses and rapid transitions need separate tests.</li><li>No overtopping, rain, soil, drains, intervention effects or GPU integration.</li><li>Boundary formulations differ between HLL and the candidate, so discrepancies cannot all be attributed to interior transport.</li><li>Passing permanent-wall fixtures does not validate real bridge geometry.</li></ul>
<h2>Regional boundary inputs</h2><p>The CORA extraction retrieved 73 hourly modeled values at 34 nodes covering September 5-8, 2019. Only 97 of the 256 geometric perimeter points have valid contributing vertices for the entire interval. Missing or dry nodes remain null; no fallback or zero filling was applied. Model MSL has not been converted to NAVD88. Physical open-water face selection is still required.</p>
<p>Dorian's sensor traces remain unread, but a published creek high-water mark was exposed during prior research. Any improvement informed by Dorian requires a different untouched event before a general accuracy claim.</p>
<p><a href="results.json">All scores, volumes and gates</a> · <a href="protocol.json">Frozen experiment</a> · <a href="reference-refinement/results.json">Refinement results</a> · <a href="../dorian-2019/cora-forcing-candidate-v1/results.json">CORA candidate levels and validity</a> · <a href="../index.html">Validation dashboard</a></p>
<p>Method context: <a href="https://www.sciencedirect.com/science/article/pii/S0022169410001538">Bates et al., local-inertial formulation</a> and <a href="https://gmd.copernicus.org/articles/18/843/2025/">SFINCS subgrid research</a>. This is an isolated implementation, not copied solver code.</p></main></html>'''
(ROOT/'report.html').write_text(html,encoding='utf-8');print(ROOT/'report.html')
