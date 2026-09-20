import {test,expect} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
test('completed simulated comparison exports a reproducible report and safe readable HTML',async({page})=>{
 await page.goto('/');const report=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {simulate,buildReport,inputIdentity,unpackInput,evidenceFiles}=await import(path);
  const n=16,input={nx:4,ny:4,dx:1,dy:1,z:new Float32Array(n),solid:new Uint8Array(n),rainWeights:new Float32Array(n).fill(1),roughness:new Float32Array(n),capacity:new Float32Array(n),infiltration:new Float32Array(n),maxStepS:10,spatialOrder:2};
  const storm={duration:1,recession:1,depth:.2},frames:any[]=[];
  const f=await simulate(input,storm,new AbortController().signal,(frame:any)=>frames.push(frame));
  const score=f.maxDepth.reduce((sum:number,h:number)=>sum+Math.max(0,h-.1),0),hash=await inputIdentity(input);
  const result={baselineScore:score,plannedScore:score,designs:[],evidence:{storm,maxStepS:10,baselineInputHash:hash,plannedInputHash:hash,assessmentExcludedCells:[],budgetMinor:100000,engine:'webgl2-hll-order2',createdAt:'2026-09-11',baselineLedger:f.ledger,plannedLedger:f.ledger}};
  const ring=[[[-2,-2],[-1,-2],[-1,-1],[-2,-1],[-2,-2]]];
  const bundle={bundle_id:'controlled-saved-comparison',extent_m:4,buildings:[
   {id:'valued',geometry:{type:'Polygon',coordinates:ring},height_m:3,base_elevation_m:0,exterior_cells:[0],first_floor_elevation_m:0,structure_value_minor:10000,damage_curve:{id:'controlled',source:'controlled fixture',points:[[0,0],[.2,.5],[1,1]]}},
   {id:'unvalued',geometry:{type:'Polygon',coordinates:ring},height_m:3,base_elevation_m:0,exterior_cells:[1]}
  ],candidates:[],quality:{},grid:{nx:4,ny:4,dx_m:1,dy_m:1,origin_x_m:500000,origin_y_m:2800000,crs:'EPSG:32644',row_direction:'north'},label:'Controlled report verification case',assumptions:['Synthetic flat terrain; no site calibration.']};
  const request={input,plannedInput:input,baseline:frames,planned:frames,result,provenance:bundle};
  const report=await buildReport(request);
  const storagePath='/src/completed-comparison.ts';const storage=await import(storagePath);
  const saved={version:1,savedAt:new Date().toISOString(),report:request,context:{bundle,input,designs:[{id:'saved-garden',kind:'rain_garden',cells:[0],eligibility:'user_assumed',excavationM:.1,storageDepthM:.1,conductivityMS:.00001,percolationMS:0,roughness:.05,costMinor:1000,parameterSource:'Controlled saved candidate'}],flood:{mode:'rain',inflows:[],outlets:[],source:''},rain:200,minutes:1/60,importedStorm:{name:'Controlled storm',duration_s:1,recession_s:1,depth_m:.2},budget:1000,city:null,contextStatus:'Controlled fixture'}};
  await storage.saveCompletedComparison(saved);
  let rejected=false;
  try{await storage.saveCompletedComparison({...saved,report:{...request,result:{...result,plannedScore:score+1}}});}catch{rejected=true;}
  if(!rejected)throw new Error('Invalid completed comparison was saved');
  const restored=unpackInput(JSON.parse(JSON.stringify(report.scenario.baselineInput)));const replayed=await simulate(restored,storm,new AbortController().signal);
  return {exports:await evidenceFiles(report),html:report.html,scenario:report.scenario,rerunError:Math.max(...replayed.depth.map((h:number,i:number)=>Math.abs(h-f.depth[i])))};
 });
 expect(report.rerunError).toBe(0);
 expect(report.exports.manifest.model.sourceTreeSha256).toMatch(/^[0-9a-f]{64}$/);
 let staleContextCancelled=false;
 page.on('requestfailed',request=>{if(request.url().endsWith('/context'))staleContextCancelled=true;});
 const contextStarted=page.waitForRequest(request=>request.url().endsWith('/context'));
 await page.route('**/api/v1/bundles/*/context',()=>{});
 await page.reload();
 await contextStarted;
 await page.getByRole('button',{name:'Restore saved comparison',exact:true}).click();
 await expect(page.getByRole('dialog',{name:'Storm comparison'})).toBeVisible();
 await expect.poll(()=>staleContextCancelled).toBe(true);
 await page.unroute('**/api/v1/bundles/*/context');
 await expect(page.getByRole('heading',{name:'Controlled report verification case',exact:true})).toBeVisible();
 await expect(page.getByRole('slider',{name:'Replay time'})).toHaveAttribute('max','120');
 await page.getByRole('slider',{name:'Replay time'}).fill('120');
  await expect(page.getByText('valuation coverage 50.0%',{exact:false}).first()).toBeVisible();
  await expect(page.getByText('monetary loss $50',{exact:false}).first()).toBeVisible();
  await expect(page.getByText('2 buildings at or above 10 cm',{exact:false}).first()).toBeVisible();
  await expect(page.getByLabel('Modelled intervention effects at replay time')).toContainText('Water at intervention locations');
  await expect(page.getByText('footprint colours and storage pulses are driven by the planned solver frame',{exact:false})).toBeVisible();
  await expect(page.getByText('Highlighted footprints',{exact:false})).toBeVisible();
  await page.getByLabel('Exposure depth threshold').selectOption('0.3');
 await expect(page.getByText('0 buildings at or above 30 cm',{exact:false}).first()).toBeVisible();
 await page.evaluate(()=>{(window as any).__printedReport='';window.open=(()=>({document:{open(){},write(value:string){(window as any).__printedReport=value;},close(){}},focus(){},setTimeout(callback:()=>void){callback();},print(){(window as any).__printCalled=true;},close(){}})) as any;});
 await page.getByRole('button',{name:'Print / save PDF'}).click();
 await expect.poll(()=>page.evaluate(()=>(window as any).__printCalled===true)).toBe(true);
 expect(await page.evaluate(()=>(window as any).__printedReport)).toContain('SPONGE · Stormwater planning report');
 await page.getByRole('button',{name:'Close comparison'}).click();
 await page.getByRole('button',{name:'Compare selected design',exact:true}).click();
 await expect(page.getByText('Completed comparison saved in this browser.',{exact:true})).toBeVisible({timeout:30000});
 await page.reload();
 await page.getByRole('button',{name:'Restore saved comparison',exact:true}).click();
 await expect(page.getByRole('dialog',{name:'Storm comparison'})).toContainText('Assumed installation cost: $10');
 await page.getByRole('button',{name:'Close comparison'}).click();
 await page.getByRole('button',{name:'Discard saved comparison'}).click();
 await expect(page.getByRole('button',{name:'Restore saved comparison',exact:true})).toHaveCount(0);
 await page.reload();
 await expect(page.getByRole('button',{name:'Restore saved comparison',exact:true})).toHaveCount(0);
 await mkdir('artifacts/verification/export-set',{recursive:true});
 for(const [name,content] of Object.entries(report.exports.files)){
  if(typeof content!=='string')throw new Error('Export must contain text files');
  await writeFile('artifacts/verification/export-set/'+name,content);
 }
 await writeFile('artifacts/verification/export-set/sponge-export-manifest.json',JSON.stringify(report.exports.manifest,null,2));
 await mkdir('artifacts/verification',{recursive:true});await writeFile('artifacts/verification/planning-report.html',report.html);await writeFile('artifacts/verification/reproducible-comparison.json',JSON.stringify(report.scenario));
 await page.setContent(report.html);await expect(page.getByRole('heading',{name:'SPONGE · Stormwater planning report'})).toBeVisible();await expect(page.locator('svg')).toHaveCount(2);await expect(page.getByText('Damage valuation is unavailable.',{exact:false})).toBeVisible();
 await page.screenshot({path:'artifacts/verification/planning-report.png',fullPage:true});
});


test('report accepts evaluated intervention physics and rejects altered excavation',async({page})=>{
 await page.goto('/');const result=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {simulate,buildReport,inputIdentity,compileDesign}=await import(path);
  const input={nx:4,ny:4,dx:5,dy:5,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16).fill(.03),capacity:new Float32Array(16),infiltration:new Float32Array(16),maxStepS:10};
  const design={id:'garden',kind:'rain_garden',cells:[0],eligibility:'user_assumed',excavationM:.1,storageDepthM:.1,conductivityMS:.00001,percolationMS:0,roughness:.05,costMinor:10000,parameterSource:'controlled test'};
  const plannedInput=compileDesign(input,[design],10000),storm={duration:1,recession:1,depth:.2};
  const baseline:any[]=[],planned:any[]=[];
  const b=await simulate(input,storm,new AbortController().signal,(f:any)=>baseline.push(f));
  const p=await simulate(plannedInput,storm,new AbortController().signal,(f:any)=>planned.push(f));
  const score=(f:any)=>f.maxDepth.reduce((s:number,h:number,i:number)=>s+(i?Math.max(0,h-.1)*25:0),0);
  const request={input,plannedInput,baseline,planned,provenance:{label:'evaluated garden'},result:{designs:[design],baselineScore:score(b),plannedScore:score(p),evidence:{storm,maxStepS:10,budgetMinor:10000,baselineInputHash:await inputIdentity(input),plannedInputHash:await inputIdentity(plannedInput),assessmentExcludedCells:[0]}}};
  const report=await buildReport(request);let rejected=false;
  try{await buildReport({...request,result:{...request.result,designs:[{...design,excavationM:.2}]}});}catch(e){rejected=String(e).includes('do not reproduce');}
  if(!report.html.includes('Eligibility basis')||!report.csv.includes('user_assumed'))throw new Error('Export lost eligibility basis');
  return {cost:report.scenario.summary.costMinor,count:report.scenario.selectedDesigns.length,rejected};
 });
 expect(result).toEqual({cost:10000,count:1,rejected:true});
});


test('coastal comparison retains boundary levels, datum and water exclusions through save and export',async({page})=>{
 await page.goto('/');const result=await page.evaluate(async()=>{
  const harness='/src/testing/gpu-harness.ts',scenarioPath='/src/scenario-input.ts',storagePath='/src/completed-comparison.ts';
  const {simulate,buildReport,inputIdentity,unpackInput}=await import(harness),{scenarioInput}=await import(scenarioPath),storage=await import(storagePath);
  const base={nx:4,ny:4,dx:1,dy:1,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16),roughness:new Float32Array(16).fill(.03),capacity:new Float32Array(16),infiltration:new Float32Array(16),maxStepS:.05,spatialOrder:2};
  const city={roads:[],green:[],trees:[],assumptions:[],water:[{id:'test-water',name:'test',polygon:[[-2,-2],[-1,-2],[-1,2],[-2,2],[-2,-2]]}]};
  const flood={mode:'coastal',inflows:[],outlets:[],source:'synthetic',coastal:{edge:'west',cells:[0,4,8,12],levels:[{timeS:0,elevationM:.1},{timeS:.5,elevationM:.2},{timeS:1,elevationM:.1}],source:'synthetic coastal test',datum:'local synthetic metres'}};
  const input=scenarioInput(base,flood,city),storm={duration:1,recession:1,depth:0},frames:any[]=[];
  const frame=await simulate(input,storm,new AbortController().signal,(f:any)=>frames.push(f));
  const score=frame.maxDepth.reduce((s:number,h:number,i:number)=>s+(input.planningWaterMask[i]?0:Math.max(0,h-.1)),0),hash=await inputIdentity(input);
  const result={baselineScore:score,plannedScore:score,designs:[],evidence:{storm,maxStepS:.05,baselineInputHash:hash,plannedInputHash:hash,assessmentExcludedCells:[],budgetMinor:0,engine:'webgl2-hll-order2',createdAt:'2026-09-12'}};
  const bundle={bundle_id:'coastal-report-test',grid:{nx:4,ny:4,dx_m:1,dy_m:1,origin_x_m:0,origin_y_m:0,crs:'EPSG:32644'},label:'Synthetic coastal test',assumptions:[]};
  const request={input,plannedInput:input,baseline:frames,planned:frames,result,provenance:bundle},report=await buildReport(request);
  await storage.saveCompletedComparison({version:1,savedAt:new Date().toISOString(),context:{bundle,input:base,designs:[],flood,rain:0,minutes:1/60,importedStorm:null,budget:0,city,contextStatus:'test'},report:request});
  const saved=await storage.readCompletedComparison(),packed=unpackInput(JSON.parse(JSON.stringify(report.scenario.baselineInput)));
  const packedHash=await inputIdentity(packed);
  const originalAgain=await simulate(input,storm,new AbortController().signal);
  const rerun=await simulate(packed,storm,new AbortController().signal);
  console.log('Coastal replay identity',JSON.stringify({originalHash:hash,packedHash,originalRerunError:Math.max(...originalAgain.depth.map((h:number,i:number)=>Math.abs(h-frame.depth[i]))),packedRerunError:Math.max(...rerun.depth.map((h:number,i:number)=>Math.abs(h-frame.depth[i])))}));
  if(packedHash!==hash)throw new Error('Export changed coastal input identity');
  return {originalHash:hash,packedHash,originalRerunError:Math.max(...originalAgain.depth.map((h:number,i:number)=>Math.abs(h-frame.depth[i]))),datum:saved.report.input.coastal.datum,mask:[...packed.planningWaterMask],html:report.html,error:Math.max(...rerun.depth.map((h:number,i:number)=>Math.abs(h-frame.depth[i]))),residual:frame.ledger.relative_residual};
 });
 console.log('Coastal replay diagnostic',JSON.stringify({originalHash:result.originalHash,packedHash:result.packedHash,originalRerunError:result.originalRerunError,packedRerunError:result.error}));
 expect(result.datum).toBe('local synthetic metres');expect(result.mask.filter(x=>x===1)).toHaveLength(4);expect(result.html).toContain('synthetic coastal test');expect(result.html).toContain('prescribed coastal level on west');expect(result.originalRerunError).toBe(0);expect(result.error).toBe(0);expect(result.residual).toBeLessThan(.00001);
});
