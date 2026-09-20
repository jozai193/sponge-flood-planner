"""Render retained event cohorts and explicit acceptance decisions."""
import html
import json
from pathlib import Path

root=Path('artifacts/validation');sections=[];decisions=[]
fmt=lambda x:'Unavailable' if x is None else f'{x:.4f}'
for event in ('irma-2017','ian-2022','sandy-2012'):
    candidate=root/(event+'-grid128');path=candidate/'regression-comparison.json'
    if not path.exists():
        failure=candidate/'replay-failure-diagnosis.json'
        if failure.exists() and not json.loads(failure.read_text())['accepted_for_accuracy']:
            diagnostic=json.loads(failure.read_text());decisions.append(False)
            sections.append(f'<section><h2>{html.escape(event)}</h2><p><strong>Raw replay rejected; no accepted accuracy comparison.</strong> {html.escape(diagnostic["raw_audit"]["error"])}</p><p>The original output and frozen acceptance criteria are retained. A roundoff sensitivity diagnosis does not convert this into a pass.</p><p><a href="{event}-grid128/replay-failure-diagnosis.json">Failure diagnosis</a></p></section>')
        else:
            sections.append(f'<section><h2>{html.escape(event)}</h2><p>Candidate comparison pending. No improvement inferred.</p></section>')
        continue
    gate=json.loads(path.read_text());decisions.append(gate['regression_gate_passed'])
    old=json.loads((root/event/'accuracy.json').read_text())['runs'][-1]
    new=json.loads((candidate/'accuracy.json').read_text())['runs'][-1]
    lookup={s['observation_id']:s for s in new['samples']};rows=[]
    for a in old['samples']:
        b=lookup[a['observation_id']]
        rows.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in (
            a['observation_id'],a['status'],b['status'],fmt(a.get('error_m')),fmt(b.get('error_m'))))+'</tr>')
    verdict='Passes this event’s regression checks' if gate['regression_gate_passed'] else 'Fails this event’s regression checks'
    picture=f'<img src="{event}-grid128/grid-comparison.png" alt="Both resolutions with shared water-depth colours and retained observations" style="max-width:100%">' if (candidate/'grid-comparison.png').exists() else ''
    sections.append(f'''<section><h2>{event}</h2><p><strong>{verdict}</strong></p>
<p>Common wet-point RMSE: {fmt(gate['baseline_common_rmse_m'])} → {fmt(gate['candidate_common_rmse_m'])} m.
Dry misses: {gate['dry_before']} → {gate['dry_after']}. Lost supported observations: {html.escape(str(gate.get('lost_supported_ids',[])))}.</p>
<p>Candidate wet cohort: {new['compared_count']} of {new['total_count']} retained marks. Model RMSE on those marks: {fmt(new['rmse_m'])} m; gauge-only reference on the same marks: {fmt(new['gauge_only_baseline']['rmse_m'])} m. This reference uses the gauge peak at each location and does not predict inundation. Common-point regression and candidate-cohort error answer different questions.</p>
<div class="scroll"><table><thead><tr><th>USGS mark</th><th>64-grid status</th><th>128-grid status</th><th>64 error m</th><th>128 error m</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
{picture}
<p><a href="{event}/inspection.html">64-grid replay</a> · <a href="{event}-grid128/inspection.html">128-grid replay</a> · <a href="{event}-grid128/regression-comparison.json">Full checks</a></p></section>''')
    for name in (event,event+'-grid128'):
        diagnosis=root/name/'point-diagnosis.json'
        if diagnosis.exists():
            points=json.loads(diagnosis.read_text())['observations']
            sections.append('<details><summary>'+name+' terrain and gauge diagnostics</summary><ul>'+''.join(
                '<li>'+html.escape(f"{s['observation_id']}: model minus native ground {fmt(s['model_minus_native_ground_m'])} m; model water minus gauge peak {fmt(s.get('model_peak_minus_gauge_peak_m'))} m; {s['status']}")+'</li>' for s in points)+'</ul><p>Same-source terrain checks are not independent ground truth. Unsupported locations have no accepted prediction error.</p></details>')
    initialization=candidate/'initialization-diagnosis.json'
    if initialization.exists():
        diag=json.loads(initialization.read_text())
        rows=''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in (c['terrain'],c['buildings'],f"{c['connected_initial_area_m2']:,.0f}",f"{c['initial_volume_m3']:,.0f}"))+'</tr>' for c in diag['cases'])
        sections.append(f'<details><summary>{event}: why initial connectivity changes</summary><table><thead><tr><th>Terrain</th><th>Building mask</th><th>Connected area m²</th><th>Initial volume m³</th></tr></thead><tbody>{rows}</tbody></table><p>{html.escape(diag["limitation"])}</p></details>')
title='Candidate fails a retained event check' if not all(decisions) else 'Candidate checks pending, including Sandy prior-event regression' if len(decisions)<3 else 'Candidate passes the three retained event checks; general accuracy remains unvalidated'
doc=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SPONGE resolution comparison</title>
<style>body{{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42;margin:0}}main{{max-width:1100px;margin:auto;padding:28px}}section,details{{background:white;padding:22px;border:1px solid #cad6d0;margin:18px 0;border-radius:8px}}.notice{{background:#fff0d7;padding:18px;border-left:4px solid #b97828}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}.scroll{{overflow:auto}}a{{color:#006b85}}</style>
<main><h1>Does a finer grid generalize?</h1><p class="notice"><strong>{title}.</strong> Production defaults have not changed. Sparse point comparisons do not validate city-wide flood extent, depth or timing.</p>
<p>Candidate: 128 × 128 instead of 64 × 64 cells. Each event keeps its own domain: 2 km for Ian and Irma, 1 km for Sandy. Native source terrain, footprints, gauge forcing, roughness and observation coordinates remain fixed. Building and terrain rasterization change with resolution. Sandy is an already exposed prior-event regression, not a fresh independent test.</p>
<p>A pass requires no lost wet or supported points, no increased dry misses, passing mass balance and no more than 0.01 m worsening in common-point or equal-site RMSE. This tolerance is an engineering threshold, not measurement uncertainty. Newly wet points need individual review.</p>
{''.join(sections)}<p><a href="index.html">All historical runs</a> · <a href="refinement-decision.json">Machine-readable decision</a></p></main></html>'''
(root/'refinement-report.html').write_text(doc,encoding='utf-8')
print(title)
