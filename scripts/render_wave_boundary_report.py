"""Show the isolated outgoing-wave test without claiming historical accuracy."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path('artifacts/validation/wave-boundary-v1')
result=json.loads((root/'results.json').read_text())
protocol=json.loads((root/'protocol.json').read_text())
for path,digest in protocol['source_sha256'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
data=json.loads((root/'profiles-east.json').read_text())
fig,axes=plt.subplots(2,1,figsize=(10,7),layout='constrained')
colors={'long_reference':'#263d44','prescribed_stage':'#c14d31','characteristic':'#137b88'}
labels={'long_reference':'Longer reference channel','prescribed_stage':'Existing prescribed stage','characteristic':'Characteristic candidate'}
for key in data:
    h=np.asarray(data[key])
    axes[0].plot(np.arange(80)+.5,(h[-1]-1)*1000,label=labels[key],color=colors[key])
    if key!='long_reference':
        error=np.sqrt(np.mean((h-np.asarray(data['long_reference']))**2,axis=1))*1000
        axes[1].plot(np.arange(31),error,label=labels[key],color=colors[key])
axes[0].set(xlabel='Distance along short channel (m)',ylabel='Stage above background (mm)',title='Final state after the pulse exits the short channel')
axes[1].set(xlabel='Time (s)',ylabel='Stage RMSE against longer channel (mm)',title='Same initial pulse and discretization; no fitted parameters')
for ax in axes:ax.legend();ax.grid(alpha=.2)
fig.savefig(root/'reflection-comparison.png',dpi=140)
metrics=[r for r in result['results'] if 'ratio' in r]
rows=''.join(f"<tr><td>{r['orientation']}</td><td>{r['final_stage_rmse_baseline_m']*1000:.4f}</td><td>{r['final_stage_rmse_candidate_m']*1000:.4f}</td><td>{r['ratio']:.6f}</td><td>{r['rmse_gate_passed']}</td></tr>" for r in metrics)
doc=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Coastal wave boundary experiment</title>
<style>body{{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42;margin:0}}main{{max-width:1050px;margin:auto;padding:28px}}img{{max-width:100%}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #bbc9c7}}.notice{{background:#fff0d7;padding:18px}}a{{color:#006b85}}.scroll{{overflow-x:auto}}</style><main>
<h1>Suppressing artificial boundary reflections</h1><p class="notice">Synthetic numerical test only. Production remains unchanged. An incoming-wave signal is not interchangeable with a measured total water-level record.</p>
<p>A 2 cm outgoing pulse crosses an 80 m channel edge. A 160 m channel with identical spacing supplies the reference before the pulse reaches its far edge. Existing fixed-stage forcing creates a returning trough; the characteristic candidate lets most of the pulse leave.</p>
<img src="reflection-comparison.png" alt="Final returning wave and error through time, comparing existing and characteristic boundary conditions with a longer reference channel">
<div class="scroll"><table><tr><th>Outgoing direction</th><th>Existing RMSE (mm)</th><th>Candidate RMSE (mm)</th><th>Error ratio</th><th>Fixed gate passed</th></tr>{rows}</table></div>
<p>The criterion was fixed before running: candidate error at most 25% of the existing boundary's error, relative mass residual at most 1e-10, nonnegative depth, and rotation difference at most 1e-12 m. Numerical gate passed: <b>{result['numerical_gate_passed']}</b>. East-to-north rotation difference: {result['rotation_max_difference_m']:.3g} m.</p>
<h2>What changed</h2><p>The isolated CPU candidate combines the outgoing characteristic from the interior with a specified incoming wave relative to a still background. It retains the existing face-flux water ledger and named segment accounting. The implementation rejects unsupported dry and supercritical states, and rejects records labelled as total-gauge-stage forcing.</p>
<p>The equations follow the <a href="https://anuga.readthedocs.io/en/develop/reference/generated/anuga.Characteristic_wave_boundary.html">published ANUGA characteristic-boundary description</a>. This is a local normal-flow approximation; oblique waves, arbitrary mean currents and wet/dry boundary transitions remain unvalidated. No third-party solver was installed or run.</p>
<h2>Historical validation still required</h2><p>Do not feed our NOAA total-level hydrographs into this incoming-wave mode. Distinct ocean/sound boundary forcing still requires appropriate observations or an outer model. The prior segmented stage candidate remains available for total-level experiments.</p>
<p>The numerical and contract suite passes 186 tests, including seven new characteristic-boundary checks. The earlier Okushiri result remains a preserved test of the stage-segment candidate; it has not been rerun with this new wave-boundary interpretation.</p>
<p><a href="protocol.json">Frozen protocol and hashes</a> · <a href="results.json">Every run and ledger</a> · <a href="../okushiri-lab/report.html">Earlier laboratory comparison</a> · <a href="../dorian-2019/sensor-review.html">New Dorian sensor evidence screen</a> · <a href="../index.html">Validation dashboard</a></p></main></html>'''
(root/'report.html').write_text(doc,encoding='utf-8');print(root/'report.html')
