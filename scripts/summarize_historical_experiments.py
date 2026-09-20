"""Summarize retained cohorts and source diagnostics without pooling unlike events."""
import json
from pathlib import Path

root=Path('artifacts/validation');rows=[]
for name in ('sandy-2012','michael-2018','ian-2022','irma-2017','irma-2017-grid128','ian-2022-grid128','sandy-2012-grid128','matthew-2016'):
    path=root/name/'accuracy.json'
    if not path.exists():continue
    a=json.loads(path.read_text())
    for r in a['runs']:
        wet=[s for s in r['samples'] if s['status']=='compared']
        supported=[s for s in r['samples'] if s['status'] in ('compared','observed_flood_model_dry')]
        base=r['gauge_only_baseline']['rmse_m']
        rows.append({'event': name,'grid_cells': r['grid_cells'],'total_marks': r['total_count'],'supported_marks': len(supported),'wet_compared': len(wet),
            'dry_misses': r['missed_flood_count'],'unresolved': r['total_count']-len(supported),
            'rmse_m': r['rmse_m'],'same_wet_gauge_rmse_m': base,
            'rmse_difference_from_gauge_m': r['rmse_m']-base if r['rmse_m'] is not None and base is not None else None,
            'worst_compared_error_m': max((abs(s['error_m']) for s in wet),default=None),
            'mass_gate_passed': r['mass_gate_passed']})
out={'rows': rows,'interpretation': 'Negative RMSE difference means lower error than the gauge-only reference on the same wet points. This is not a significance test or proof of generalization. Do not pool events or grids; preserve unsupported and dry locations.'}
(root/'cross-event-results.json').write_text(json.dumps(out,indent=2))
lines=['# Historical flood comparison results','',out['interpretation'],'',
    '| Event | Grid | Wet / supported / total | Dry | Unresolved | RMSE m | Gauge-only m | Mass gate |',
    '|---|---:|---:|---:|---:|---:|---:|---|']
fmt=lambda x:'Unavailable' if x is None else f'{x:.3f}'
for r in rows:
    lines.append(f'| {r["event"]} | {r["grid_cells"]} | {r["wet_compared"]} / {r["supported_marks"]} / {r["total_marks"]} | {r["dry_misses"]} | {r["unresolved"]} | {fmt(r["rmse_m"])} | {fmt(r["same_wet_gauge_rmse_m"])} | {"Passed" if r["mass_gate_passed"] else "FAILED"} |')
lines+=['','Michael indoor marks are unsupported; its preliminary RMSE was withdrawn. Sally had no local Pensacola marks in the checked STN response. Ian and Irma use frozen manual setting reviews.','',
    'The simulations omit important coastal processes, and point maxima do not validate city-wide extent, timing or depth. Actual physics improvements require a recorded hypothesis, prior-case regression and a fresh-event check.']
(root/'cross-event-results.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(out,indent=2))
