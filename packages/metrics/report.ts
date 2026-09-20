import {assessScenarioData} from '../domain/data-admission';
import {validationStatus} from './validation-status';
import {parseScenarioSpec,assessScenario,sameScenarioValue} from '../domain/scenario-wire';
import {compileDesign} from '../domain/interventions';
import {validateRainfall} from '../simulation/src/rainfall';
import {inputIdentity} from '../simulation/src/identity';
import {validateGPUInput,type GPUInput} from '../simulation/src/gpu';
import {floodScore} from '../simulation/src/experiment';

export interface ReportFrame {time_s:number;depth:Float32Array;maxDepth:Float32Array;ledger:Record<string,number>}
export interface ReportRequest {input:GPUInput;plannedInput:GPUInput;baseline:ReportFrame[];planned:ReportFrame[];result:any;provenance:any}
const arrayKeys=['z','solid','rainWeights','roughness','infiltration','capacity','percolation','depth','planningWaterMask'] as const;
export function packInput(input:GPUInput){const out:any={...input};for(const key of arrayKeys)if(input[key])out[key]={encoding:(key==='solid'||key==='planningWaterMask')?'uint8':'float32',values:Array.from(input[key]!)};return out;}
export function unpackInput(packed:any):GPUInput{const out={...packed};for(const key of arrayKeys)if(out[key]){const a=out[key];if(!Array.isArray(a.values)||a.values.length>2048*2048||a.encoding!==((key==='solid'||key==='planningWaterMask')?'uint8':'float32'))throw new Error('Invalid scenario array');if(a.values.some((v:unknown)=>typeof v!=='number'||!Number.isFinite(v)||((key==='solid'||key==='planningWaterMask')&&(!Number.isInteger(v)||(v!==0&&v!==1)))))throw new Error('Invalid scenario value');out[key]=(key==='solid'||key==='planningWaterMask')?new Uint8Array(a.values):new Float32Array(a.values);}validateGPUInput(out);return out;}
const escape=(value:unknown)=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
const number=(value:number)=>Number.isFinite(value)?value.toLocaleString('en-US',{maximumFractionDigits:3}):'Unavailable';
function validateFrame(frame:ReportFrame,input:GPUInput,previous?:ReportFrame){
 const {depth,maxDepth,ledger}=frame;
 if(!Number.isFinite(frame.time_s)||depth.length!==input.z.length||maxDepth.length!==input.z.length||depth.some(v=>!Number.isFinite(v)||v<0)||maxDepth.some(v=>!Number.isFinite(v)||v<0))throw new Error('Invalid or unconserved report frame');
 let surface=0;
 for(let cell=0;cell<depth.length;cell++){
  if(maxDepth[cell]+1e-6<depth[cell]||(previous&&maxDepth[cell]+1e-6<previous.maxDepth[cell]))throw new Error('Invalid report peak history');
  if(input.solid[cell]&&(depth[cell]>1e-6||maxDepth[cell]>1e-6))throw new Error('Report water inside solid cells');
  if(!input.solid[cell])surface+=depth[cell]*input.dx*input.dy;
 }
 const keys=['initial_m3','rain_m3','inflow_m3','stored_m3','surface_m3','subsurface_m3','outflow_m3','deep_percolation_m3','residual_m3','relative_residual'];
 if(keys.some(key=>!Number.isFinite(ledger[key])||(key!=='residual_m3'&&ledger[key]<0)))throw new Error('Invalid or unconserved report frame ledger');
 const close=(actual:number,expected:number,relative=2e-6,absolute=1e-5)=>Math.abs(actual-expected)<=absolute+relative*Math.abs(expected);
 if(!close(surface,ledger.surface_m3)||!close(ledger.stored_m3,ledger.surface_m3+ledger.subsurface_m3))throw new Error('Report depth and water ledger do not reconcile');
 const supplied=ledger.initial_m3+ledger.rain_m3+ledger.inflow_m3,residual=supplied-ledger.stored_m3-ledger.deep_percolation_m3-ledger.outflow_m3,relative=Math.abs(residual)/Math.max(supplied,1);
 if(!close(residual,ledger.residual_m3,1e-6,1e-6)||!close(relative,ledger.relative_residual,1e-6,1e-10)||relative>.001)throw new Error('Invalid or unconserved report frame ledger');
}
function peakMap(input:GPUInput,frame:ReportFrame){
 let cells='';for(let i=0;i<frame.maxDepth.length;i++){const h=frame.maxDepth[i];if(!input.solid[i]&&h<.005)continue;const t=Math.min(1,h/.6);const color=input.solid[i]?'#5d6669':`rgb(${Math.round(49-32*t)},${Math.round(190-95*t)},${Math.round(218-53*t)})`;cells+=`<rect x="${i%input.nx}" y="${input.ny-1-Math.floor(i/input.nx)}" width="1" height="1" fill="${color}"/>`;}
 return `<svg role="img" aria-label="Peak flood depth map, north up" viewBox="0 0 ${input.nx} ${input.ny}" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#e6ece2"/>${cells}</svg>`;
}
export async function buildReport(request:ReportRequest){
 const {result,baseline,planned,provenance}=request,e=result.evidence;
 if(!e?.storm||!e.baselineInputHash||!e.plannedInputHash)throw new Error('Completed run evidence is required');
 validateRainfall(e.storm);
 if(!Number.isSafeInteger(e.budgetMinor)||e.budgetMinor<0)throw new Error('Invalid report budget');
 const step=e.maxStepS??(e.candidateDesigns?.some((d:any)=>d.surfaceControl?.rating)?.2:request.input.maxStepS??10);
 const input={...request.input,maxStepS:step},plannedInput={...request.plannedInput,maxStepS:step};
 validateGPUInput(input);validateGPUInput(plannedInput);
 if(input.nx!==plannedInput.nx||input.ny!==plannedInput.ny||input.dx!==plannedInput.dx||input.dy!==plannedInput.dy)throw new Error('Comparison grids differ');
 if(await inputIdentity(input)!==e.baselineInputHash||await inputIdentity(plannedInput)!==e.plannedInputHash)throw new Error('Report input hashes do not match evaluated inputs');
 if(e.scenario){
  const spec=parseScenarioSpec(e.scenario),f=spec.forcing,d=spec.domain;
  const same=sameScenarioValue;
  if(!assessScenario(spec).compatible||spec.execution_input_hash!==e.baselineInputHash||
     e.engine!==spec.engine+'-order'+(input.spatialOrder??1)||d.nx!==input.nx||d.ny!==input.ny||d.dx_m!==input.dx||d.dy_m!==input.dy||
     !same(f.coastal??null,input.coastal??null)||!same(f.inflows,input.inflows??[])||!same(f.outlets,input.outlets??[])||
     f.storm.duration!==e.storm.duration||f.storm.recession!==e.storm.recession||f.storm.depth!==e.storm.depth||!same(f.storm.intervals??null,e.storm.intervals??null))throw new Error('Scenario envelope does not match evaluated inputs and storm');
 }
 const designs=result.designs??[];
 const reconstructed=compileDesign(input,designs,e.budgetMinor);
 // The compiler materializes an absent percolation array as zero; both mean zero loss.
 const normalized=(value:GPUInput)=>({...value,percolation:value.percolation??new Float32Array(value.nx*value.ny)});
 if(await inputIdentity(normalized(reconstructed))!==await inputIdentity(normalized(plannedInput)))throw new Error('Exported designs do not reproduce the evaluated planned input');
 const end=e.storm.duration+e.storm.recession;
 if(!baseline.length||baseline.length!==planned.length)throw new Error('Incomplete paired replay');
 for(let i=0;i<baseline.length;i++){
  validateFrame(baseline[i],input,baseline[i-1]);validateFrame(planned[i],plannedInput,planned[i-1]);
  if(Math.abs(baseline[i].time_s-planned[i].time_s)>1e-5||(i>0&&baseline[i].time_s<=baseline[i-1].time_s))throw new Error('Replay time mismatch');
 }
 if(Math.abs(baseline[0].time_s)>1e-7||Math.abs(baseline.at(-1)!.time_s-end)>1e-5)throw new Error('Report requires the full storm and recession');
 const b=baseline.at(-1)!,p=planned.at(-1)!,mask=new Set<number>(e.assessmentExcludedCells??[]);
 for(const cell of mask)if(!Number.isInteger(cell)||cell<0||cell>=input.z.length)throw new Error('Invalid assessment mask');
 const candidates=e.candidateDesigns??designs;
 if(!Array.isArray(candidates))throw new Error('Invalid candidate evidence');
 const candidateIds=new Set<string>(),expectedMask=new Set<number>();
 for(const candidate of candidates){
  if(candidateIds.has(candidate.id))throw new Error('Duplicate candidate evidence');
  candidateIds.add(candidate.id);
  compileDesign(input,[candidate],Number.MAX_SAFE_INTEGER);
  for(const cell of candidate.cells)expectedMask.add(cell);
 }
 if(mask.size!==expectedMask.size||[...mask].some(cell=>!expectedMask.has(cell)))throw new Error('Assessment mask does not match candidate areas');
 for(const design of designs){
  const candidate=candidates.find((d:any)=>d.id===design.id);
  if(!candidate)throw new Error('Selected design missing from candidate evidence');
  if(candidate.costMinor!==design.costMinor||candidate.eligibility!==design.eligibility||candidate.parameterSource!==design.parameterSource||JSON.stringify(candidate.costBreakdown??null)!==JSON.stringify(design.costBreakdown??null)||JSON.stringify(candidate.candidateEvidence??null)!==JSON.stringify(design.candidateEvidence??null))throw new Error('Selected design assumptions differ from candidate evidence');
 }
 for(const f of [b,p])for(const key of ['surface_m3','subsurface_m3','outflow_m3','deep_percolation_m3'])if(!Number.isFinite(f.ledger[key])||f.ledger[key]<-1e-6)throw new Error('Missing report ledger');
 const scores=[floodScore(b,input,mask),floodScore(p,plannedInput,mask)];
 if(scores.some((v,i)=>{const reported=[result.baselineScore,result.plannedScore][i];return !Number.isFinite(v)||!Number.isFinite(reported)||Math.abs(v-reported)>1e-6*Math.max(1,v);}))throw new Error('Report scores do not reconcile');
 let cost=0;for(const d of designs){if(!Number.isSafeInteger(d.costMinor)||d.costMinor<0)throw new Error('Invalid cost');cost+=d.costMinor;}if(cost>e.budgetMinor)throw new Error('Plan exceeds its budget');
 const localWorsening=p.maxDepth.reduce((sum,h,i)=>sum+(!input.solid[i]&&!input.planningWaterMask?.[i]&&!mask.has(i)&&h-b.maxDepth[i]>=.05?input.dx*input.dy:0),0);
 const rows=[['Peak excess-depth score (m³ proxy)',...scores],['Final surface water (m³)',b.ledger.surface_m3,p.ledger.surface_m3],['Final subsurface water (m³)',b.ledger.subsurface_m3,p.ledger.subsurface_m3],['External discharge (m³)',b.ledger.outflow_m3,p.ledger.outflow_m3],['Deep percolation (m³)',b.ledger.deep_percolation_m3,p.ledger.deep_percolation_m3],['Relative mass error (%)',100*b.ledger.relative_residual,100*p.ledger.relative_residual]];
 const dataAssessment=e.scenario?assessScenarioData(e.scenario,provenance):null;
 if(e.scenario?.domain.bundle_id&&dataAssessment&&!dataAssessment.exploratory_allowed)throw new Error('Report terrain provenance does not match the evaluated scenario');
 const dataHtml=dataAssessment?'<h2>Scenario data suitability</h2><p>Metadata screen: '+escape(dataAssessment.status)+'. Observed flood accuracy remains unvalidated.</p><ul>'+dataAssessment.checks.map(c=>'<li><strong>'+escape(c.id.replaceAll('_',' '))+':</strong> '+escape(c.reason)+' '+escape(c.action)+'</li>').join('')+'</ul>':'<h2>Scenario data suitability</h2><p>Not assessed: this legacy comparison has no shared scenario envelope.</p>';
 const stormEvidence=e.storm.evidence;
 if(stormEvidence){
  const ci=stormEvidence.confidence_interval;
  if(!Number.isFinite(stormEvidence.estimate_mm)||stormEvidence.estimate_mm<0||!Number.isFinite(stormEvidence.location?.latitude)||!Number.isFinite(stormEvidence.location?.longitude)||
    (ci&&(!Number.isFinite(ci.level)||ci.level<=0||ci.level>=1||!Number.isFinite(ci.lower_mm)||!Number.isFinite(ci.upper_mm)||ci.lower_mm>stormEvidence.estimate_mm||ci.upper_mm<stormEvidence.estimate_mm)))throw new Error('Invalid storm source evidence');
 }
 const stormHtml=stormEvidence?`<h2>Rainfall source and uncertainty</h2><p><strong>${escape(stormEvidence.product)}</strong> from ${escape(stormEvidence.provider)}. Point estimate ${number(stormEvidence.estimate_mm)} mm${stormEvidence.confidence_interval?`; ${number(stormEvidence.confidence_interval.level*100)}% confidence interval ${number(stormEvidence.confidence_interval.lower_mm)}–${number(stormEvidence.confidence_interval.upper_mm)} mm`:''}. Location ${number(stormEvidence.location.latitude)}, ${number(stormEvidence.location.longitude)} (${escape(stormEvidence.location.label)}).${Number.isFinite(stormEvidence.annual_exceedance_probability)?` Annual exceedance probability ${number(stormEvidence.annual_exceedance_probability*100)}%.`:''}</p><p>${escape(stormEvidence.spatial_support)} ${escape(stormEvidence.temporal_distribution_source)} ${escape(stormEvidence.stationarity_note??'')}</p><p class="muted">Retrieved ${escape(stormEvidence.retrieved_at)} · source ${escape(stormEvidence.source_url)} · SHA-256 <code>${escape(stormEvidence.source_sha256)}</code></p>`:`<h2>Rainfall source and uncertainty</h2><p>User-defined or imported rainfall; no verified precipitation-frequency evidence is attached. No return period is claimed.</p>`;
 const robust=e.robustPlanning,robustHtml=robust?`<h2>Robust planning sensitivity</h2><p>Every alternative was evaluated against the same ${robust.members.length}-member rainfall-depth sensitivity ensemble (${robust.members.map((m:any)=>number(m.sensitivity_factor*100)+'%').join(', ')} of the point event). The objective used the worst member. These factors are sensitivities, not probabilities.${robust.noBenefit?' No tested plan improved the disclosed worst-case score; no benefit is claimed.':''}</p>`:'';
 const costRows=designs.map((d:any)=>{const c=d.costBreakdown;return `<tr><td>${escape(d.id)}</td><td>${escape(d.kind)}</td><td>${number(d.costMinor/100)}</td><td>${c?`${number(c.sitePreparationMinor/100)} / ${number(c.materialsMinor/100)} / ${number(c.installationMinor/100)} / ${number(c.contingencyMinor/100)}`:'Legacy total only'}</td><td>${c?number(c.annualMaintenanceMinor/100):'Unavailable'}</td><td>${escape(c?`${c.priceYear} · ${c.basis}`:'Not itemised')}</td><td>${escape(d.eligibility)} · ${escape(d.candidateEvidence?.sourceNote??'Legacy evidence')}</td><td>${escape(d.parameterSource)}</td></tr>`}).join('');
 const annualMaintenance=designs.reduce((sum:number,d:any)=>sum+(d.costBreakdown?.annualMaintenanceMinor??0),0);
 const scenario={dataAssessment,schema:'sponge-reproducible-comparison',version:1,validation:validationStatus,evidence:e,summary:{baselineScore:scores[0],plannedScore:scores[1],costMinor:cost,annualMaintenanceMinor:annualMaintenance,localWorseningAreaM2:localWorsening},baselineInput:packInput(input),plannedInput:packInput(plannedInput),selectedDesigns:designs,provenance,outputs:{timesSeconds:baseline.map(f=>f.time_s),baselineFinal:{depth:Array.from(b.depth),maxDepth:Array.from(b.maxDepth),ledger:b.ledger},plannedFinal:{depth:Array.from(p.depth),maxDepth:Array.from(p.maxDepth),ledger:p.ledger}}};
 const html=`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SPONGE planning report</title><style>body{font:15px/1.5 system-ui;color:#193d3d;max-width:1000px;margin:40px auto;padding:0 24px}h1{font-size:34px}h2{margin-top:30px}small,.muted{color:#536b68}.maps{display:grid;grid-template-columns:1fr 1fr;gap:24px}svg{width:100%;max-height:390px;border:1px solid #b7cac6}table{border-collapse:collapse;width:100%;margin:18px 0}td,th{padding:9px;border-bottom:1px solid #ccd8d3;text-align:left}th{background:#e7efe8}code{overflow-wrap:anywhere;font-size:11px}.notice{padding:16px;background:#edf4e9;border-left:4px solid #527c58}@media print{body{margin:0;max-width:none;font-size:11px}.maps,table,tr{break-inside:avoid}h2{break-after:avoid}button{display:none}}@page{size:A4;margin:16mm}</style><body><h1>SPONGE · Stormwater planning report</h1><p>${escape(provenance.label??'Neighbourhood comparison')} · ${escape(e.createdAt)}</p><p class="notice">${escape(validationStatus.summary)} Results are not a calibrated flood forecast, engineered design, grant eligibility determination or monetary damage estimate.</p><h2>Decision and alternatives</h2><p>Compared the baseline with ${designs.length} selected interventions under the same storm. The peak excess-depth score ${scores[1]<scores[0]?'decreased':scores[1]>scores[0]?'increased':'did not change'} from ${number(scores[0])} to ${number(scores[1])} m³. This is a sum of cell-wise peaks above 10 cm outside candidate areas and mapped permanent water, not simultaneous flood volume.</p><p>Assumed capital cost: $${number(cost/100)} USD; budget $${number(e.budgetMinor/100)} USD; itemised annual maintenance $${number(annualMaintenance/100)} USD where supplied. Damage valuation is unavailable. Search status: ${escape(e.searchResult?.status??'manual comparison')}${e.searchResult?`; ${number(e.searchResult.evaluations)} completed evaluations in ${number(e.searchResult.elapsedMs)} ms. ${escape(e.searchResult.terminationReason)}`:'.'}</p>${robustHtml}<table><thead><tr><th>Metric</th><th>Baseline</th><th>Planned</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${escape(r[0])}</td><td>${number(r[1] as number)}</td><td>${number(r[2] as number)}</td></tr>`).join('')}</tbody></table><h2>Peak depth maps</h2><div class="maps"><div><h3>Baseline</h3>${peakMap(input,b)}</div><div><h3>Planned</h3>${peakMap(plannedInput,p)}</div></div><p class="muted">North up. Pale cyan to dark blue: 0–0.6 m and above. Grey: solid building cells. Maps show each cell's maximum over the whole run, not one simultaneous water surface.</p><h2>Residual risk and next data needs</h2><p>${number(localWorsening)} m² outside candidate areas has at least 5 cm higher peak depth in the planned run. Inspect downstream effects before choosing a plan. Facilities can saturate; maintenance, clogging and underdrain condition can change performance.</p><p>Obtain surveyed terrain and outlet elevations, verified drainage capacity, soil infiltration tests, parcel eligibility, sourced installation/maintenance costs and observed flood measurements before engineering decisions. Test additional storms and antecedent saturation; this remains screening, not a probabilistic forecast.</p>${dataHtml}${stormHtml}<h2>Scenario and assumptions</h2><p>${number(e.storm.depth*1000)} mm over ${number(e.storm.duration/60)} minutes, followed by ${number(e.storm.recession/60)} minutes of recession. Initial soil saturation: ${number((input.saturation??0)*100)}%. Temporal pattern: ${escape(e.storm.distribution??(e.storm.intervals?'imported intervals':'uniform'))}. Grid ${input.nx} × ${input.ny}, ${number(input.dx)} × ${number(input.dy)} m cells. Engine: ${escape(e.engine)}. Boundaries: ${escape(input.coastal?'prescribed coastal level on '+input.coastal.edge+'; other edges closed':input.boundary??'closed')}. ${input.coastal?'Coastal source: '+escape(input.coastal.source)+'. Datum: '+escape(input.coastal.datum)+'. Levels (seconds / local metres): '+escape(JSON.stringify(input.coastal.levels))+'. Exploratory reservoir forcing; no validated surge or tsunami prediction.':''}</p><ul>${(provenance.assumptions??[]).map((a:unknown)=>`<li>${escape(a)}</li>`).join('')}</ul><p>${escape(e.initialSoilCondition)} ${escape(e.facilityModel)}</p><h2>Selected designs and costs</h2><table><tr><th>Design</th><th>Type</th><th>Capital USD</th><th>Prep / materials / install / contingency</th><th>Annual O&amp;M</th><th>Price year and basis</th><th>Eligibility evidence</th><th>Parameter source</th></tr>${costRows}</table><h2>Evidence identities</h2><p>Baseline <code>${escape(e.baselineInputHash)}</code><br>Planned <code>${escape(e.plannedInputHash)}</code></p><p>The companion scenario JSON contains exact float32 inputs, forcing, selected designs, source metadata, final depths and ledgers. Use it to reproduce and compare outcomes; device-dependent floating-point differences may occur.</p></body></html>`;
 const csv='design_id,kind,capital_usd,site_preparation_usd,materials_usd,installation_usd,contingency_usd,annual_maintenance_usd,price_year,cost_basis,eligibility,parcel_ids,candidate_source,parameter_source\r\n'+designs.map((d:any)=>{const c=d.costBreakdown??{};return[d.id,d.kind,(d.costMinor/100).toFixed(2),c.sitePreparationMinor===undefined?'':(c.sitePreparationMinor/100).toFixed(2),c.materialsMinor===undefined?'':(c.materialsMinor/100).toFixed(2),c.installationMinor===undefined?'':(c.installationMinor/100).toFixed(2),c.contingencyMinor===undefined?'':(c.contingencyMinor/100).toFixed(2),c.annualMaintenanceMinor===undefined?'':(c.annualMaintenanceMinor/100).toFixed(2),c.priceYear??'',c.basis??'',d.eligibility,(d.candidateEvidence?.parcelIds??[]).join('|'),d.candidateEvidence?.sourceNote??'',d.parameterSource].map(v=>'"'+String(v??'').replace(/"/g,'""').replace(/^[=+@-]/,"'")+'"').join(',')}).join('\r\n');
 return {html:html
  .replace('<th>Eligibility evidence</th>','<th>Eligibility basis and evidence</th>')
  .replace('</style>','@page{size:A4;margin:16mm 16mm 22mm}@media print{ul{break-inside:avoid}p{orphans:3;widows:3}}</style>'),scenario,csv};
}
