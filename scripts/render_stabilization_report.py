"""Render product checks and subsequent live-runtime recovery evidence."""
import html
import json
from pathlib import Path

root=Path('artifacts/verification/stabilization-v1')
r=json.loads((root/'verification.json').read_text())
before,after=r['load_before'],r['load_after']
rows=''.join(f'<tr><td>{"First browser load" if i==0 else "Warm process / new page "+str(i)}</td>'
    f'<td>{before["controls_ms"][i]/1000:.2f} s</td><td>{after["controls_ms"][i]/1000:.2f} s</td>'
    f'<td>{before["max_long_task_ms"][i]:.0f} → {after["max_long_task_ms"][i]:.0f} ms</td>'
    f'<td>{after["full_detail_callback_ms"][i]/1000:.2f} s</td></tr>' for i in range(3))
replay=''.join(f'<tr><td>{label}</td><td>{v["renderedStates"]}/{v["expectedStates"]}</td><td>{v["p95StateIntervalMs"]:.1f} ms</td>'
    f'<td>{v["maxStateIntervalMs"]:.1f} ms</td><td>{v["fenceFailures"]}</td></tr>' for label,v in r['replay'].items())
limits=''.join(f'<li>{html.escape(x)}</li>' for x in r['limits'])
live_path=root/'live-verification.json'
live_notice='<div class="notice">The original prepared-data checks excluded Docker and API availability.</div>'
if live_path.exists():
    live=json.loads(live_path.read_text())
    live_notice=f'''<h2>Docker recovered · live checks passed</h2>
<p>14 September follow-up: the inaccessible sailor-ingest.sock prevented Docker startup. The guarded repair preserved and recreated runtime socket directories.
Docker Engine 29.7.2 is running; four containers, nine images and the SPONGE data volumes remain. PostgreSQL, Redis, API and worker are healthy.</p>
<p><strong>11 browser tests passed</strong>, covering real sample loading, storm stop/resume, controlled water-coverage failures, live enrichment and access controls, survey import, report evidence and exact synthetic coastal replay reproduction.
A new authenticated preparation job completed with 688 buildings. All six downloaded arrays matched generated files; water coverage, audit and an external imagery tile were checked. Provider caches were retained.</p>
<p>The live browser imported a synthetic 20-second rain / 10-second recession event, evaluated both subsets of one candidate, downloaded all five files, restored the comparison and played to its final state.
The candidate slightly worsened the score, so the planner selected no construction at $0. This verifies selection behavior, not real-event accuracy.</p>
<p>Export checks: {live['export_manifest_files']} checksum-matched files. Both exported simulations reproduced final depth and peak depth exactly on this device.</p>
<p><a href="live-verification.json">Live verification summary</a> · <a href="docker-recovery.json">Docker recovery</a> · <a href="live-api.json">Live API and queue</a> ·
<a href="live-browser-tests.log">11 browser tests</a> · <a href="live-export-set/sponge-planning-report.html">Live planner export</a> · <a href="live-export-rerun.log">Export rerun</a></p>
<img src="../../../output/playwright/live-recovery-planner.png" alt="Live app planner at final replay state after Docker recovery">
<p>The socket workaround is not an upstream Docker fix. These functional tests do not establish general flood accuracy, reboot-cold performance, clean installation or submission readiness.</p>'''
page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SPONGE stabilization checks</title><style>
body{{margin:0;background:#eef3f0;color:#193a35;font:16px/1.65 system-ui}}main{{max-width:1100px;padding:36px;margin:auto}}
h1{{font-size:38px;line-height:1.15}}h2{{margin-top:32px}}a{{color:#08785e}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}
article{{background:white;border:1px solid #d1dfd7;border-radius:12px;padding:18px}}article strong{{display:block;font-size:21px}}
.notice{{padding:18px;background:#fff0d5;border-left:5px solid #ab7800}}table{{width:100%;border-collapse:collapse;background:white;font-size:14px}}
th,td{{text-align:left;padding:12px;border-bottom:1px solid #d6e1db}}.scroll{{overflow:auto}}img{{width:100%;border-radius:8px}}
</style><main><p>SPONGE / product stabilization / 14 September 2026</p><h1>Physics preserved. Product checks completed.</h1>
<div class="cards"><article><strong>HLL unchanged</strong>Five production source hashes verified. Experimental graph methods remain separate.</article>
<article><strong>Responsiveness improved with limits</strong>Staged map layers reduce the longest first-load stall. Full detail arrives later.</article>
<article><strong>Planning + exports verified</strong>Budget rejection, eligibility assumptions, search, downloads and restore checked on prepared data.</article>
<article><strong>Limits visible</strong>App and exports explicitly retain unvalidated flood accuracy and unavailable damage valuation.</article></div>
<h2>Fresh NVIDIA measurements</h2><p>Before and after: prepared Spring Garden, Philadelphia; Chrome; 1440 × 960 development server.
No provider downloads, API latency or satellite imagery. Three pages share a browser process in each batch; this is not a reboot-cold test.</p>
<div class="scroll"><table><tr><th>Sample</th><th>Controls before</th><th>Controls after</th><th>Longest main-thread task</th><th>Full detail drawn after</th></tr>{rows}</table></div>
<p>The first observed controls improved from 2.94 to 1.78 seconds, but warm controls were slower, about 0.94–0.96 seconds rather than 0.75–0.76.
The first complete detail callback is 3.04 seconds after navigation. The remaining 0.55-second task is still noticeable.
Staging changes when work happens; it does not eliminate cold graphics setup or establish faster total loading.</p>
<h2>Actual paired replay</h2><p>Replay now retains geometry when only the camera changes, has separate lighting effects for each canvas,
and respects the selected pixel-quality setting. Balanced replay omits dynamic shadows; High detail retains them.</p>
<div class="scroll"><table><tr><th>View</th><th>Saved states drawn in order</th><th>95th percentile transition</th><th>Longest transition</th><th>Failed GPU fences</th></tr>{replay}</table></div>
<p>Target interval is 150 ms. Both views displayed all 121 sampled states. This is stepped replay, not a 60 FPS claim.
Instrumentation now starts before the first replay draw and excludes time spent waiting for the user to press Play.</p>
<h2>Planning evidence that reconciles</h2><p>The browser refused applying a site without the explicit eligibility assumption, and refused comparing a $10,000 design against a $0 budget.
At a $10,000 budget it completed both the manual comparison and the single-candidate exhaustive search (two subsets).
The short synthetic storm is a functional fixture, not a representative rainfall accuracy test.</p>
<p>Both export sets have four checksum-matched files. Installation cost appears once per design, not once per each of its 25 model cells.
The manual export rerun reproduced baseline and planned final depths and peaks exactly on this device. The report validator now rejects invented assessment exclusions and altered candidate cost/eligibility claims.</p>
<p><a href="export-set/sponge-planning-report.html">Downloaded manual report</a> · <a href="plan-export-set/sponge-planning-report.html">Downloaded planner report</a> ·
<a href="plan-export-set/sponge-export-manifest.json">Planner export manifest</a> · <a href="export-rerun.log">Independent export rerun</a></p>
<img src="../../../output/playwright/stabilization-planner.png" alt="Actual SPONGE paired replay with planning score, cost assumptions and accuracy limits">
<h2>Validation and remaining work</h2><p><strong>49 TypeScript tests, typecheck and production build passed.</strong> The prior 227 Python tests were not repeated for this UI-only pass;
the frozen production physics files remain byte-identical. Build retains its large-main-bundle warning.</p>
{live_notice}<ul>{limits}</ul>
<p><a href="verification.json">Machine-readable checks</a> · <a href="solver-freeze.json">Physics freeze</a> · <a href="load-before.json">Before load samples</a> ·
<a href="load-final.json">After load samples</a> · <a href="replay-verified.json">Replay draws</a> · <a href="../../validation/index.html">Scientific validation dashboard</a></p></main></html>'''
(root/'report.html').write_text(page,encoding='utf-8')
print(root/'report.html')
