// Experimental candidate runner; original frozen runner remains unchanged.
import {chromium} from '@playwright/test';
import {readFile,writeFile,access,rename} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root=process.argv[2];
if(!root)throw Error('Usage: node scripts/run-historical-validation.mjs <experiment-directory>');
const sha=b=>createHash('sha256').update(b).digest('hex');
const runnerHash=sha(await readFile(new URL(import.meta.url)));
const bytes=await readFile(`${root}/protocol.json`),protocol=JSON.parse(bytes);
if(sha(bytes)!=(await readFile(`${root}/protocol.sha256`,'utf8')).trim())throw Error('Protocol checksum mismatch');
async function verifySources(){for(const [path,hash] of Object.entries(protocol.source_sha256??{}))if(sha(await readFile(path))!==hash)throw Error(`Frozen input changed: ${path}`);}
await verifySources();
const browser=await chromium.launch({channel:'chrome'});
try{
 for(const run of protocol.bundles){
  const output=`${root}/simulation-${run.grid_cells}.json`;
  try{await access(output);throw Error('Refusing to overwrite '+output);}catch(e){if(e.code!=='ENOENT')throw e;}
  const folder=`data/local/bundles/${run.bundle_id}`;
  const manifest=JSON.parse(await readFile(`${folder}/manifest.json`,'utf8'));
  const checkpointPath=`${root}/checkpoint-${run.grid_cells}.json`;
  let resume=null;
  try{
   const envelope=JSON.parse(await readFile(checkpointPath,'utf8'));
   if(sha(envelope.payload)!==envelope.sha256)throw Error('Checkpoint checksum mismatch');
   resume=JSON.parse(envelope.payload);
   if(resume.protocolHash!==sha(bytes)||resume.runnerHash!==runnerHash)throw Error('Checkpoint protocol or runner changed');
   console.log('Resuming checkpoint at physical seconds',resume.checkpoint.time);
  }catch(e){if(e.code!=='ENOENT')throw e;}
  const page=await browser.newPage();
  await page.route('**/?historical-validation',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><title>Historical numerical validation</title>'}));
  await page.route('**/validation-array/*',async route=>{
   const name=new URL(route.request().url()).pathname.split('/').at(-1);
   if(!['z','solid'].includes(name))throw Error('Unexpected array');
   await route.fulfill({body:await readFile(`${folder}/${name}.bin`)});
  });
  await page.exposeFunction('recordProgress',async progress=>{
   await writeFile(`${root}/progress.json`,JSON.stringify({grid:run.grid_cells,...progress}));
   console.log(JSON.stringify({grid:run.grid_cells,...progress}));
  });
  await page.exposeFunction('saveCheckpoint',async state=>{
   const payload=JSON.stringify({...state,protocolHash:sha(bytes),runnerHash});
   await writeFile(checkpointPath+'.tmp',JSON.stringify({sha256:sha(payload),payload}));
   await rename(checkpointPath+'.tmp',checkpointPath);
   if(process.argv.includes('--stop-after-checkpoint'))throw Error('Intentional checkpoint recovery verification stop');
  });
  await page.goto('http://127.0.0.1:5173/?historical-validation');
  const result=await page.evaluate(async({run,manifest,protocol,resume})=>{
   const {inputIdentity,coastalInitialDepth}=await import('/src/testing/gpu-harness.ts');
   const {GPUSolver}=await import('/@fs/E:/Nextstep Hacks hackathon/packages/simulation/src/gpu-positivity-candidate.ts');
   const [zBytes,solidBytes]=await Promise.all(['z','solid'].map(async name=>(await fetch('/validation-array/'+name)).arrayBuffer()));
   const nx=manifest.grid.nx,ny=manifest.grid.ny,n=nx*ny,edge=protocol.boundary_edge??'west';
   const solid=new Uint8Array(solidBytes);
   const cells=Array.from({length:n},(_,i)=>i).filter(i=>!solid[i]&&(edge==='west'?i%nx===0:edge==='east'?i%nx===nx-1:edge==='south'?i<nx:i>=n-nx));
   const input={nx,ny,dx:manifest.grid.dx_m,dy:manifest.grid.dy_m,z:new Float32Array(zBytes),solid,
    rainWeights:new Float32Array(n),roughness:new Float32Array(n).fill(protocol.roughness),
    capacity:new Float32Array(n),infiltration:new Float32Array(n),spatialOrder:2,maxStepS:protocol.max_step_s,
    coastal:{edge,cells,levels:run.levels,datum:'NAVD88 minus '+manifest.grid.elevation_origin_m+' m',source:protocol.forcing}};
   input.depth=coastalInitialDepth(input,input.coastal);
   const identity=await inputIdentity(input),solver=new GPUSolver(input),started=performance.now(),frames=resume?.frames??[];
   let next=resume?.next??0,lastProgress=started;
   try{
    if(resume){
     const c=resume.checkpoint;
     await solver.restore({...c,state:new Float32Array(c.state),history:new Float32Array(c.history)});
     if(resume.renderer.renderer!==solver.info().renderer)throw Error('Checkpoint renderer changed; use a separately recorded comparison');
    }
    while(solver.time<protocol.duration_s-1e-7){
     if(solver.time>=Math.min(protocol.duration_s,next)-1e-7){
      const f=solver.frame();frames.push({time_s:f.time_s,depth:Array.from(f.depth),maxDepth:Array.from(f.maxDepth),ledger:f.ledger});
      next+=protocol.duration_s/120;
      // Save at existing output boundaries, preserving the original timestep
      // schedule. Atomic replacement leaves the last good checkpoint intact.
      if(frames.length%4===0){
       const c=await solver.checkpoint();
       await window.saveCheckpoint({checkpoint:{...c,state:Array.from(c.state),history:Array.from(c.history)},
        frames,next,renderer:solver.info(),elapsedMs:(resume?.elapsedMs??0)+performance.now()-started});
      }
     }
     const target=Math.min(protocol.duration_s,next);
     for(let batch=0;batch<100&&solver.time<target-1e-7;batch++)solver.step(Math.min(protocol.max_step_s,target-solver.time),0);
     if(performance.now()-lastProgress>10000){lastProgress=performance.now();await window.recordProgress({simulatedHours:solver.time/3600,wallSeconds:(performance.now()-started)/1000,steps:solver.steps});}
     await new Promise(resolve=>setTimeout(resolve,0));
    }
    const f=solver.frame();frames.push({time_s:f.time_s,depth:Array.from(f.depth),maxDepth:Array.from(f.maxDepth),ledger:f.ledger});
    return {bundle_id:run.bundle_id,grid:manifest.grid,inputHash:identity,renderer:solver.info(),elapsedMs:(resume?.elapsedMs??0)+performance.now()-started,steps:f.steps,ledger:f.ledger,frames,coastal:input.coastal,
      resumedFromTimeS:resume?.checkpoint.time??null};
   }finally{solver.dispose();}
  },{run,manifest,protocol,resume});
  await verifySources();
  result.protocol_sha256=sha(bytes);
  result.runner_sha256=runnerHash;
  await writeFile(output,JSON.stringify(result),{flag:'wx'});
  console.log('Completed',run.grid_cells,JSON.stringify({wallSeconds:result.elapsedMs/1000,steps:result.steps,ledger:result.ledger}));
  await page.close();
 }
}finally{await browser.close();}
