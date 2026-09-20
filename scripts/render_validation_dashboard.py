"""Build the scientific comparison index from current saved evidence."""

import json
from pathlib import Path

root=Path('artifacts/validation')

events=[]

for name in ('sandy-2012','michael-2018','ian-2022','irma-2017','irma-2017-grid128','ian-2022-grid128','sandy-2012-grid128','matthew-2016'):

    p=root/name/'protocol.json'

    if p.exists():

        c=json.loads(p.read_text())

        events.append({'directory': name,'title': c['city']+' Ã‚Â· '+c['event_id']+(' Ã‚Â· 128-grid candidate' if 'grid128' in name else ''),'hours': c['duration_s']/3600,'grids': [r['grid_cells'] for r in c['bundles']]})

template='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SPONGE historical validation</title>

<style>body{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42;margin:0}main{max-width:1100px;margin:auto;padding:30px}h1{margin-bottom:0}.notice{padding:15px;background:#fff0d7;border-left:4px solid #b97828}.cards{display:grid;grid-template-columns:1fr 1fr;gap:20px}article{padding:22px;background:#fff;border:1px solid #cad6d0;border-radius:8px}h2{margin-top:0;font-size:21px}dt{color:#526d70}dd{margin:0 0 8px;font-size:21px}a{color:#006b85}progress{width:100%;height:20px}small{color:#52676a}@media(max-width:650px){.cards{display:block}article{margin-bottom:18px}main{padding:16px}}</style>

<main><h1>Historical flood comparisons</h1><p>SPONGE Ã‚Â· frozen inputs Ã‚Â· retained observations Ã‚Â· reproducible checks</p>

<p class="notice"><strong>Real-world accuracy remains unvalidated.</strong> Mass conservation, water-level error and flood-extent accuracy measure different things. Indoor, ambiguous and building-cell observations remain unresolved. A dry-miss count of zero is not success when there are no supported comparisons.</p>

<p id="file-warning" hidden>Live status requires the local server. <a href="http://127.0.0.1:5173/@fs/E:/Nextstep%20Hacks%20hackathon/artifacts/validation/index.html">Open the served dashboard</a>.</p>

<div class="cards" id="cards"></div>

<h2>Free data and GIS workflow</h2><p><a href="free-data-workflow/index.html">Source audit and Dorian GIS review layers</a>. Primary tile coverage, acquisition-date conflicts and explicit limits on which evidence can support flood-area scores.</p>

<h2>Independent laboratory benchmark</h2><p><a href="okushiri-lab/report.html">Okushiri measured wave traces and isolated boundary-segment candidate</a>. Two fixed resolutions; CPU diagnostic only, with production adoption held pending independent historical validation.</p>

<h2>Boundary reflection and next-event sensors</h2><p><a href="wave-boundary-v1/report.html">Characteristic wave boundary versus a longer reference channel</a> · <a href="dorian-2019/input-audit.html">Dorian input audit: coordinate conflicts and creek geometry</a>. NetCDF units and time are verified; the historical comparison has not started. Numerical improvement and observation screening are separate evidence.</p>
<h2>Terrain storage and regional forcing</h2><p><a href="subgrid-storage-v1/report.html">Subgrid terrain storage on two domains</a> · <a href="dorian-2019/cora-boundary-preflight.html">CORA perimeter mapping and datum uncertainty</a>. Storage is experimental and has no flow solver integration. A public creek high-water mark was exposed during research; Dorian is now diagnostic evidence, not a fully untouched event. Sensor traces remain unread.</p>
<h2>Dorian benchmark readiness</h2><p><a href="dorian-2019/bridge-geometry-review/report.html">Recovered June 2019 Slash Creek profile and quantified forcing gaps</a>. The relative pre-storm channel profile is available, but the old rail-to-NAVD88 tie and continuous creek geometry are unresolved. Across reviewed datum offsets, 79–82 potentially submerged boundary faces lack complete forcing. No historical accuracy run or terrain change is admitted.</p>
<p><a href="dorian-2019/domain-boundary-screen-v1/report.html">Six nested-domain boundary screens</a>: 2/3/4 km at two grid sizes improve regional forcing coverage, but all retain unsupported potentially submerged faces. At 128 cells the central-offset gap drops from 45.7% to 22.1%. No domain is adopted; this is input support, not observed accuracy.</p>
<h2>Controlled flow tests</h2><p><a href="compartment-flow-v1/report.html">Connected compartments versus fine-grid HLL</a>. Initial gates passed, but a finer dry-front diagnosis found premature shallow wetting caused in part by coarse grouping. The candidate is withheld from historical and production use. CORA extraction retains missing values and is not yet an admitted physical boundary.</p>
<p><a href="refined-compartment-v1/report.html">Selective refinement: regression plus two new synthetic fronts</a>. Smaller cells fix the original downstream dry mismatch, but a new island-channel case fails arrival limits and the mixed wet/dry case worsens two gauge errors. Production adoption remains withheld.</p>
<p><a href="momentum-boundary-v1/report.html">Momentum and boundary mechanism diagnosis</a>. Nine open/closed equation comparisons plus an attempted boundary exchange replay. Removing HLL advection does not reproduce graph early arrival; exact boundary matching failed and is not treated as valid control. Keep the production HLL baseline.</p>

<h2>New-event generalization check</h2><p><a href="matthew-2016/holdout-report.html">Matthew 2016 Ã‚Â· Charleston Ã‚Â· frozen 64/128 comparison</a>. All observations remain in the audit, including missing-datum and building-cell exclusions.</p>

<h2>Numerical positivity candidate</h2><p><a href="positivity-report.html">Reference checks and live full-event regressions</a>. Experimental only; original failed runs remain preserved.</p>

<h2>Domain-size diagnostic</h2><p><a href="matthew-2016-domain4km/experiment-report.html">4 km versus 2 km at identical cell spacing and core inputs</a>. Exposed Matthew development test; live status and fixed evaluation criteria.</p>

<h2>Resolution experiment</h2><p id="refinement-state">Checking frozen candidate comparisonsÃ¢â‚¬Â¦</p><p><a href="refinement-report.html">Compare both resolutions and every observation</a> Ã‚Â· <a href="refinement-decision.json">Recorded acceptance decision when complete</a> Ã‚Â· <a href="cross-event-results.md">Cross-event results</a></p>

<h2>Evidence boundaries</h2><p>Sally was screened out: the current STN response has one Louisiana mark and no Pensacola observations. This is an availability finding for that endpoint, not proof that no Sally observations exist elsewhere. No Sally elevation was inspected.</p>

<p>Michael's preliminary score was withdrawn after both marks were identified as indoor observations. The corrected baseline has no accepted RMSE. Ian and Irma use explicit observation-setting reviews frozen before measured high-water elevations were inspected.</p>

<p>Once results guide changes, the event becomes development evidence. Improvements must retain prior-event regressions and face another event. Point marks alone cannot establish extent or timing skill.</p>

<p><a href="experiment-registry.json">Registry</a> Ã‚Â· <a href="replay-integrity-audit.json">Saved-frame audit</a> Ã‚Â· <a href="checkpoint-recovery/result.json">Recovery verification</a> Ã‚Â· <a href="iteration-005-michael.md">Michael evaluation correction</a></p>

<small>Status refreshes every 10 seconds. Unchanged progress is marked stale after a minute. Wall time is not an isolated performance benchmark.</small></main>

<script>const events=/*EVENTS*/;

const el=(tag,text)=>{const e=document.createElement(tag);if(text!=null)e.textContent=text;return e;};

async function read(path,optional=false){const r=await fetch(path+'?v='+Date.now(),{cache:'no-store'});if(optional&&(r.status===404||r.headers.get('content-type')?.includes('text/html')))return null;if(!r.ok)throw Error('Cannot read '+path);return r.json();}

if(location.protocol==='file:')document.getElementById('file-warning').hidden=false;

for(const e of events){e.card=el('article');e.card.append(el('h2',e.title));e.status=el('p','Checking saved evidenceÃ¢â‚¬Â¦');e.bar=el('progress');e.bar.max=e.hours*e.grids.length;e.bar.value=0;e.progress=el('p');e.metrics=el('dl');e.links=el('p');e.card.append(e.status,e.bar,e.progress,e.metrics,e.links);document.getElementById('cards').append(e.card);e.changed=Date.now();}

async function refresh(e){try{const [job,accuracy]=await Promise.all([read(e.directory+'/job-status.json',true),read(e.directory+'/accuracy.json',true)]);e.status.textContent=job?'Local job: '+job.stage:'Frozen inputs; not running';

if(accuracy){const r=accuracy.runs.at(-1);e.status.textContent=r.compared_count?'Completed historical screening':'Completed numerical run; no supported accuracy score';e.metrics.replaceChildren();const unresolved=r.samples.filter(s=>s.status!=='compared'&&s.status!=='observed_flood_model_dry').length;

for(const [label,value] of [['Comparable marks',r.compared_count+'/'+r.total_count],['Unresolved observations',unresolved],['Dry misses',r.missed_flood_count],['Wet-point RMSE',r.rmse_m==null?'Unavailable':r.rmse_m.toFixed(3)+' m'],['Gauge-only reference RMSE',r.gauge_only_baseline.rmse_m==null?'Unavailable':r.gauge_only_baseline.rmse_m.toFixed(3)+' m'],['Mass gate',r.mass_gate_passed?'Passed':'FAILED']])e.metrics.append(el('dt',label),el('dd',value));e.bar.value=e.bar.max;e.progress.textContent=e.grids.length+' grid run(s) complete Ã‚Â· '+e.hours+' physical hours each';e.links.replaceChildren();const a=el('a','Inspect replay and every observation');a.href=e.directory+'/inspection.html';e.links.append(a);return;}

const p=await read(e.directory+'/progress.json',true);if(p){const key=p.grid+':'+p.simulatedHours;if(key!==e.last){e.last=key;e.changed=Date.now();}const run=e.grids.indexOf(p.grid);e.bar.value=Math.max(0,run)*e.hours+p.simulatedHours;e.progress.textContent=p.grid+' Ãƒâ€” '+p.grid+' Ã‚Â· '+p.simulatedHours.toFixed(2)+' / '+e.hours+' simulated hours Ã‚Â· run '+(run+1)+' of '+e.grids.length+' Ã‚Â· '+p.steps.toLocaleString()+' steps'+(Date.now()-e.changed>60000?' Ã‚Â· progress unchanged for over one minute':'');}

if(job?.error)e.status.textContent+=' Ã‚Â· '+job.error;

}catch{e.status.textContent='Evidence unavailable; no completion inferred.';}}

async function refinement(){try{const s=await read('refinement-status.json',true);document.getElementById('refinement-state').textContent=s?'Local comparison workflow: '+s.stage+(s.decision?' Ã‚Â· '+s.decision:'')+(s.error?' Ã‚Â· '+s.error:''):'Candidate workflow not started';}catch{document.getElementById('refinement-state').textContent='Comparison status unavailable; no improvement inferred.';}}

const refreshAll=()=>Promise.all([...events.map(refresh),refinement()]);refreshAll();setInterval(refreshAll,10000);</script></html>'''

(root/'index.html').write_text(template.replace('/*EVENTS*/',json.dumps(events)),encoding='utf-8')

print('Rendered',len(events),'event cards')
