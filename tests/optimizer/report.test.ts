import {createHash} from 'node:crypto';
import {evidenceFiles} from '../../packages/metrics/evidence';
import {test,expect} from 'vitest';
import {buildReport,packInput,unpackInput,type ReportRequest} from '../../packages/metrics/report';
import {inputIdentity} from '../../packages/simulation/src/identity';
async function fixture():Promise<ReportRequest>{
 const input={nx:4,ny:4,dx:1,dy:1,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16),infiltration:new Float32Array(16),capacity:new Float32Array(16),maxStepS:10};
 const frames=[0,1].map(time_s=>({time_s,depth:new Float32Array(16).fill(time_s*.2),maxDepth:new Float32Array(16).fill(time_s*.2),ledger:{initial_m3:0,rain_m3:time_s*3.2,inflow_m3:0,stored_m3:time_s*3.2,relative_residual:0,residual_m3:0,surface_m3:time_s*3.2,subsurface_m3:0,outflow_m3:0,deep_percolation_m3:0}}));
 const hash=await inputIdentity(input),score=frames[1].maxDepth.reduce((s,v)=>s+Math.max(0,v-.1),0);
 return {input,plannedInput:input,baseline:frames,planned:frames,result:{baselineScore:score,plannedScore:score,designs:[],evidence:{storm:{duration:1,recession:0,depth:.2},maxStepS:10,baselineInputHash:hash,plannedInputHash:hash,assessmentExcludedCells:[],budgetMinor:0,engine:'test',createdAt:'2026-09-11'}},provenance:{label:'<script>alert(1)</script>',assumptions:['Unsurveyed terrain']}};
}
test('report reconciles results and exact scenario arrays survive serialization',async()=>{
 const request=await fixture(),report=await buildReport(request);
 expect(report.html).toContain('&lt;script&gt;');expect(report.html).not.toContain('<script>');expect(report.html).toContain('Peak depth maps');expect(report.scenario.summary.costMinor).toBe(0);
 const input=unpackInput(JSON.parse(JSON.stringify(packInput(request.input))));expect(await inputIdentity(input)).toBe(await inputIdentity(request.input));
});
test('reports reject missing evidence, stale input, changed scores and incomplete runs',async()=>{
 const r=await fixture();await expect(buildReport({...r,result:{...r.result,evidence:null}})).rejects.toThrow('evidence');
 await expect(buildReport({...r,input:{...r.input,roughness:new Float32Array(16).fill(.08)}})).rejects.toThrow('hash');
 await expect(buildReport({...r,result:{...r.result,plannedScore:100}})).rejects.toThrow('reconcile');
 await expect(buildReport({...r,baseline:r.baseline.slice(0,1),planned:r.planned.slice(0,1)})).rejects.toThrow('full storm');
 await expect(buildReport({...r,planned:[r.planned[0],{...r.planned[1],ledger:{relative_residual:.01}}]})).rejects.toThrow('unconserved');
});


test('scenario import rejects invalid obstacle values before Uint8 conversion can change them',async()=>{
 const r=await fixture();
 for(const value of [256,-1,.5,2]){
  const packed=packInput(r.input);packed.solid.values[0]=value;
  expect(()=>unpackInput(packed)).toThrow('Invalid scenario value');
 }
});
test('report preserves a location currency in every cost export',async()=>{
 const request=await fixture();
 request.provenance={...request.provenance,currency:'INR'};
 request.result={...request.result,evidence:{...request.result.evidence,currency:'INR'}};
 const report=await buildReport(request);
 expect(report.scenario.summary.currency).toBe('INR');
 expect(report.scenario.evidence.currency).toBe('INR');
 expect(report.html).toContain('INR');
 expect(report.csv).toContain('currency,capital');
});
test('report rejects candidate costs declared in a different currency',async()=>{
 const request=await fixture();
 request.result={...request.result,evidence:{...request.result.evidence,currency:'USD',candidateDesigns:[{id:'mixed',kind:'rain_garden',cells:[0],eligibility:'user_assumed',excavationM:0,storageDepthM:0,conductivityMS:0,percolationMS:0,roughness:0,costMinor:0,parameterSource:'fixture',costBreakdown:{sitePreparationMinor:0,materialsMinor:0,installationMinor:0,contingencyMinor:0,annualMaintenanceMinor:0,currency:'INR',priceYear:2026,basis:'fixture'}}]}};
 await expect(buildReport(request)).rejects.toThrow('currency');
});

test('report rejects nonfinite scores instead of silently passing reconciliation',async()=>{
 const r=await fixture();
 for(const plannedScore of [NaN,Infinity,undefined,'1.6'])await expect(buildReport({...r,result:{...r.result,plannedScore}})).rejects.toThrow('reconcile');
});

test('report independently checks saved depths against even a self-consistent ledger',async()=>{
 const r=await fixture(),end=r.planned[1];
 const ledger={...end.ledger,rain_m3:6.4,stored_m3:6.4,surface_m3:6.4};
 await expect(buildReport({...r,planned:[r.planned[0],{...end,ledger}]})).rejects.toThrow('depth and water ledger');
 await expect(buildReport({...r,planned:[r.planned[0],{...end,ledger:{...end.ledger,stored_m3:6.4}}]})).rejects.toThrow('depth and water ledger');
 await expect(buildReport({...r,planned:[r.planned[0],{...end,ledger:{...end.ledger,rain_m3:6.4}}]})).rejects.toThrow('unconserved');
});

test('report rejects decreasing peak history and peaks below current water',async()=>{
 const r=await fixture();
 await expect(buildReport({...r,planned:[r.planned[0],{...r.planned[1],maxDepth:new Float32Array(16).fill(.1)}]})).rejects.toThrow('peak history');
 await expect(buildReport({...r,planned:[{...r.planned[0],maxDepth:new Float32Array(16).fill(.3)},r.planned[1]]})).rejects.toThrow('peak history');
});

test('report rejects water in building cells even when hashes and claimed mass balance match',async()=>{
 const r=await fixture(),input={...r.input,solid:r.input.solid.slice(),rainWeights:r.input.rainWeights.slice()};
 input.solid[0]=1;input.rainWeights[0]=0;
 const hash=await inputIdentity(input);
 await expect(buildReport({...r,input,plannedInput:input,result:{...r.result,evidence:{...r.result.evidence,baselineInputHash:hash,plannedInputHash:hash}}})).rejects.toThrow('solid cells');
});


test('reports reject substituted designs even if reported hashes and scores are unchanged',async()=>{
 const r=await fixture();
 const design={id:'unexecuted',kind:'rain_garden',cells:[0],eligibility:'user_assumed',excavationM:.2,storageDepthM:.1,conductivityMS:.00001,percolationMS:0,roughness:.05,costMinor:0,parameterSource:'test assumption'};
 await expect(buildReport({...r,result:{...r.result,designs:[design]}})).rejects.toThrow('do not reproduce');
 await expect(buildReport({...r,result:{...r.result,evidence:{...r.result.evidence,budgetMinor:NaN}}})).rejects.toThrow('budget');
 await expect(buildReport({...r,result:{...r.result,evidence:{...r.result.evidence,storm:{duration:NaN,depth:.2,recession:0}}}})).rejects.toThrow();
});

test('report rejects invented exclusions even when the altered score reconciles',async()=>{
 const r=await fixture(),score=r.baseline[1].maxDepth.slice(1).reduce((s,h)=>s+Math.max(0,h-.1),0);
 await expect(buildReport({...r,result:{...r.result,baselineScore:score,plannedScore:score,
  evidence:{...r.result.evidence,assessmentExcludedCells:[0]}}})).rejects.toThrow('candidate areas');
});

test('portable evidence retains accuracy and valuation limits',async()=>{
 const report=await buildReport(await fixture());
 expect(report.scenario.validation.generalFloodAccuracyValidated).toBe(false);
 expect(report.scenario.validation.damage).toContain('unavailable');
 expect(report.scenario.validation.planning).toContain('included only where supplied');
 expect(report.scenario.validation.planning).not.toContain('not included');
 expect(report.html).toContain(report.scenario.validation.summary);
});

test('report rejects changed cost claims against the recorded candidate catalogue',async()=>{
 const r=await fixture();
 const design={id:'unchanged-physics',kind:'rain_garden',cells:[0],eligibility:'user_assumed',excavationM:0,storageDepthM:0,conductivityMS:0,percolationMS:0,roughness:0,costMinor:100,parameterSource:'Test cost assumption'};
 const score=r.baseline[1].maxDepth.slice(1).reduce((s,h)=>s+Math.max(0,h-.1),0);
 await expect(buildReport({...r,result:{...r.result,designs:[design],baselineScore:score,plannedScore:score,
  evidence:{...r.result.evidence,budgetMinor:100,assessmentExcludedCells:[0],candidateDesigns:[{...design,costMinor:99}]}}})).rejects.toThrow('assumptions differ');
});


test('export manifest hashes exact UTF-8 bytes and remains deterministic',async()=>{
 const request=await fixture();request.provenance={...request.provenance,bundle_id:'fixture',grid:{nx:4,ny:4,dx_m:1,dy_m:1,origin_x_m:500000,origin_y_m:2800000,crs:'EPSG:32644',row_direction:'north'},sources:[{provider:'fixture',sha256:'source-record'}]};
 const report=await buildReport(request),first=await evidenceFiles(report),second=await evidenceFiles(report);
 expect(first).toEqual(second);expect(first.manifest.artifacts).toHaveLength(4);
 for(const artifact of first.manifest.artifacts){
  const data=Buffer.from(first.files[artifact.name],'utf8');
  expect(artifact.bytes).toBe(data.length);
  expect(artifact.sha256).toBe(createHash('sha256').update(data).digest('hex'));
  expect(artifact.sha256).not.toBe(createHash('sha256').update(Buffer.concat([data,Buffer.from('changed')])).digest('hex'));
 }
 expect(first.manifest.sources).toEqual(request.provenance.sources);
 expect(first.manifest.simulation.baselineInputHash).toBe(request.result.evidence.baselineInputHash);
});
