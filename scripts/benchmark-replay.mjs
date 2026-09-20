import {chromium} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {summarizeReplayDraws} from './replay-measurements.mjs';
const id=process.argv[2]??'2c607f51e1a064fc76ee6f5585cbc343358d0e9a39ead1a2806643e21cae37ba';
if(!/^[a-f0-9]{64}$/.test(id))throw Error('Expected bundle ID');
const bundle=JSON.parse(await readFile(`data/local/bundles/${id}/manifest.json`,'utf8'));
const context=JSON.parse(await readFile(`artifacts/verification/landscape-fixtures/${id}.json`,'utf8'));
const browser=await chromium.launch({channel:'chrome'});
try{
 const page=await browser.newPage({viewport:{width:1440,height:960}});
 await page.addInitScript(()=>sessionStorage.setItem('sponge-session','prepared-benchmark-only'));
 await page.addInitScript(()=>{
  window.__draws=[];
  document.addEventListener('click',event=>{if(event.target.closest?.('button')?.textContent==='Play replay')window.__replayStarted=performance.now();},true);
  window.addEventListener('sponge-replay-draw',e=>{
   const sample={...e.detail};window.__draws.push(sample);
   const canvas=document.querySelectorAll('.replay-map canvas')[sample.label==='Baseline'?0:1],gl=canvas?.getContext('webgl2');
   if(!gl)return;
   const sync=gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE,0);gl.flush();
   function poll(){const state=gl.clientWaitSync(sync,0,0);if(state===gl.TIMEOUT_EXPIRED){requestAnimationFrame(poll);return;}sample.gpuObservedMs=performance.now();sample.fenceFailed=state===gl.WAIT_FAILED;gl.deleteSync(sync);}requestAnimationFrame(poll);
  });
 });
 await page.route('**/api/v1/bundles/**',async route=>{
  const path=new URL(route.request().url()).pathname,match=path.match(/arrays\/([a-z_]+)$/);
  if(match)return route.fulfill({body:await readFile(`data/local/bundles/${id}/${match[1]}.bin`)});
  if(path.endsWith('/context'))return route.fulfill({json:context});
  if(path.endsWith(id))return route.fulfill({json:bundle});
  return route.fulfill({status:503,json:{detail:'Imagery excluded from model replay benchmark'}});
 });
 await page.goto(`http://127.0.0.1:5173/?bundle=${id}&measure=1`);
 await page.getByRole('button',{name:'Run storm',exact:true}).waitFor();
 const simulation=await page.evaluate(async({bundle,context})=>{
  const {simulate,inputIdentity}=await import('/src/testing/gpu-harness.ts');
  const {saveCompletedComparison}=await import('/src/completed-comparison.ts');
  const arrays=await Promise.all(['z','solid','rain_weights','roughness','soil_capacity','infiltration'].map(async n=>(await fetch(`/api/v1/bundles/${bundle.bundle_id}/arrays/${n}`)).arrayBuffer()));
  const base={nx:bundle.grid.nx,ny:bundle.grid.ny,dx:bundle.grid.dx_m,dy:bundle.grid.dy_m,z:new Float32Array(arrays[0]),solid:new Uint8Array(arrays[1]),rainWeights:new Float32Array(arrays[2]),roughness:new Float32Array(arrays[3]),capacity:new Float32Array(arrays[4]),infiltration:new Float32Array(arrays[5]),spatialOrder:2,maxStepS:1};
  const {scenarioInput}=await import('/src/scenario-input.ts');
  const input=scenarioInput(base,{mode:'rain',inflows:[],outlets:[],source:''},context);
  const storm={duration:2,recession:2,depth:.02},frames=[],start=performance.now();
  const final=await simulate(input,storm,new AbortController().signal,f=>frames.push(f));
  const elapsedMs=performance.now()-start,hash=await inputIdentity(input),score=final.maxDepth.reduce((s,h,i)=>s+(input.solid[i]?0:Math.max(0,h-.1)*input.dx*input.dy),0);
  const result={baselineScore:score,plannedScore:score,designs:[],evidence:{storm,maxStepS:1,baselineInputHash:hash,plannedInputHash:hash,assessmentExcludedCells:[],budgetMinor:0,engine:'webgl2-hll-order2',createdAt:new Date().toISOString()}};
  await saveCompletedComparison({version:1,savedAt:new Date().toISOString(),report:{input,plannedInput:input,baseline:frames,planned:frames,result,provenance:bundle},context:{bundle,input:base,designs:[],flood:{mode:'rain',inflows:[],outlets:[],source:''},rain:20,minutes:2/60,importedStorm:{name:'Short performance fixture',duration_s:2,recession_s:2,depth_m:.02},budget:0,city:context,contextStatus:'Prepared benchmark context'}});
  return {elapsedMs,frames:frames.length,residual:final.ledger.relative_residual};
 },{bundle,context});
 await page.reload();
 await page.getByRole('button',{name:'Restore saved comparison',exact:true}).click();
 await page.getByRole('button',{name:'Play replay',exact:true}).waitFor();
 const renderer=await page.evaluate(()=>{const gl=document.querySelector('.replay-map canvas')?.getContext('webgl2');const ext=gl?.getExtension('WEBGL_debug_renderer_info');return ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):'unavailable';});
 await page.getByRole('button',{name:'Play replay',exact:true}).click();
 await page.waitForFunction(last=>document.querySelector('input[aria-label="Replay time"]')?.value===String(last),simulation.frames-1,{timeout:120000});
 await page.waitForFunction(last=>['Baseline','Planned'].every(label=>window.__draws.some(d=>d.label===label&&d.index===last)),simulation.frames-1,{timeout:10000});
 await page.waitForTimeout(100);
 const draws=await page.evaluate(()=>window.__draws);
 const playbackStartTime=await page.evaluate(()=>window.__replayStarted);
 const summary=summarizeReplayDraws(draws,simulation.frames,150,playbackStartTime);
 await mkdir('artifacts/verification',{recursive:true});
 const result={measuredAt:new Date().toISOString(),renderer,browserVersion:browser.version(),bundle:id,grid:bundle.grid,simulation,summary,draws,conditions:'Actual paired Replay component, prepared real terrain/buildings/context, synthetic four-second storm, identical baseline/control, installed Chrome 1440x960. Model view, imagery excluded. GPU fences polled at RAF cadence bound completion observation; not display presentation timestamps. State updates target 150ms, not 60fps.'};
 await writeFile(process.env.SPONGE_BENCHMARK_OUTPUT??'artifacts/verification/replay-draws.json',JSON.stringify({...result,playbackStartTime},null,2));
 console.log(JSON.stringify({simulation,summary}));
}finally{await browser.close();}
