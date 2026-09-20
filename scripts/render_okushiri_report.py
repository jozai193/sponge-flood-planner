"""Render the completed laboratory diagnostic with every gauge and resolution."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path('artifacts/validation/okushiri-lab')
result=json.loads((root/'results.json').read_text())
audit=json.loads((root/'integrity-audit.json').read_text())
observed=np.loadtxt(root/'output_ch5-7-9.txt',skiprows=1)
fig,axes=plt.subplots(3,1,figsize=(10,9),sharex=True,layout='constrained')
originals=[r for r in result['runs'] if r['engine']=='original']
for i,ax in enumerate(axes):
    inside=observed[:,0]<=22.5
    ax.plot(observed[inside,0],observed[inside,i+1],color='#152f34',label='Laboratory measurement',linewidth=1.4)
    for r,color in zip(originals,['#197db3','#db7428']):
        ax.plot(r['time_s'],np.asarray(r['stage_m'])[:,i]*100,color=color,label=f"SPONGE CPU {r['grid'][0]} x {r['grid'][1]}",linewidth=1.2)
    ax.set_ylabel(f"Channel {[5,7,9][i]}\nstage (cm)");ax.grid(alpha=.2)
axes[0].legend(loc='upper left');axes[-1].set_xlabel('Laboratory time (seconds)')
fig.suptitle('Okushiri physical laboratory benchmark\nFixed inputs; no time shifting or amplitude fitting')
fig.savefig(root/'gauge-comparison.png',dpi=140)
rows=''.join(f"<tr><td>{r['grid'][0]} × {r['grid'][1]}</td><td>{s['gauge']}</td><td>{s['rmse_m']*100:.3f}</td><td>{s['bias_m']*100:+.3f}</td><td>{s['peak_error_m']*100:+.3f}</td><td>{s['peak_time_error_s']:+.2f}</td></tr>" for r in originals for s in r['scores'])
candidates=[r for r in result['runs'] if r['engine']=='segments_candidate']
maxdiff=max(r['max_final_state_difference'] for r in candidates)
maxgauge=max(r['max_saved_gauge_difference_m'] for r in candidates)
mass=max(r['ledger']['relative_residual'] for r in result['runs'])
dry_samples=sum(sum(r['dry_or_unresolved_interpolated_gauge_samples']) for r in audit['run_checks'])
comparison=[]
for coarse,fine in zip(originals[0]['scores'],originals[1]['scores']):
    comparison.append(f"{coarse['gauge']}: {coarse['rmse_m']*100:.3f} → {fine['rmse_m']*100:.3f} cm")
comparison_text='; '.join(comparison)
report=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Okushiri laboratory benchmark</title>
<style>body{{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42;margin:0}}main{{max-width:1080px;margin:auto;padding:28px}}img{{width:100%}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ccd4ce}}.notice{{padding:18px;background:#fff0d7}}a{{color:#006b85}}.scroll{{overflow-x:auto}}</style><main>
<h1>Independent laboratory comparison</h1><p>Okushiri scale experiment · SPONGE CPU reference and isolated boundary candidate</p>
<p class="notice">Completed diagnostic, not a hurricane accuracy validation. Both resolutions and all three gauge traces are retained. No calibrated pass threshold, time shifting or amplitude fitting was used. The candidate is not enabled in production or on the GPU.</p>
<img src="gauge-comparison.png" alt="All three measured laboratory water-level time series compared with two fixed SPONGE grid resolutions">
<h2>Every gauge, unchanged evaluation window</h2><div class="scroll"><table><tr><th>Grid</th><th>Gauge</th><th>RMSE (cm)</th><th>Bias (cm)</th><th>Peak error (cm)</th><th>Peak-time error (s)</th></tr>{rows}</table></div>
<h2>Boundary compatibility and water accounting</h2><p>Splitting the wavemaker into two named segments with identical forcing changes final state by at most <b>{maxdiff:.3g}</b> and saved gauge stages by <b>{maxgauge:.3g} m</b>. Maximum relative mass residual across the four runs: <b>{mass:.3g}</b>. This verifies compatibility; it does not establish correct ocean/sound forcing for a real event.</p>
<p>Gauge RMSE from coarse to fine: {comparison_text}. Dry or unresolved interpolated gauge samples across all runs: {dry_samples}. <a href="integrity-audit.json">Source, time support, gauge wetness and segment accounting audit</a>.</p>
<p>Nine targeted candidate tests cover single-segment equivalence, four-sided still water, two-ended channel flow, anisotropic rotation, partial boundaries, connected initial water, restart accounting and invalid segment definitions. The combined contract/numerical suite passed 179 tests.</p>
<h2>Inputs and limits</h2><p>The domain is 5.448 × 3.402 laboratory metres, using published bathymetry, roughness 0.0025, initial stage zero and the supplied wavemaker series. Gauges are sampled by bilinear interpolation. Gauge measurements are converted from centimetres to metres. Raster resampling and our existing ghost-state boundary remain approximation sources; the GPU has not been exercised by this laboratory runner.</p>
<p>The upstream example requests 25 seconds, but its input wave ends at 22.5 seconds. The 25-second setup was rejected before simulation. The completed run uses the full supported 0–22.5 second interval. A subsequent JSON boolean serialization fix changed reporting only; both earlier protocol snapshots remain preserved.</p>
<p>The experiment reproduces laboratory measurements supplied through <a href="https://github.com/anuga-community/anuga_core/tree/33779d3cce0d6e56a712c5fbe1cf8f08cfeced8e/validation_tests/experimental_data/okushiri">ANUGA's benchmark repository</a>; original data provenance identifies CRIEPI and the Third International Workshop on Long-Wave Runup Models. No downloaded ANUGA code was executed.</p>
<p><a href="protocol.json">Fixed protocol</a> · <a href="results.json">All results and ledgers</a> · <a href="sources.json">Source hashes</a> · <a href="verification.json">Verification</a> · <a href="../index.html">Historical validation dashboard</a></p></main></html>'''
(root/'report.html').write_text(report,encoding='utf-8')
print(root/'report.html')
