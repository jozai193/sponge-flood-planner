import {chromium} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
const root='artifacts/validation/sandy-2012';
const protocol=JSON.parse(await readFile(`${root}/protocol.json`,'utf8'));
const browser=await chromium.launch({channel:'chrome'});
try{
 for(const run of protocol.bundles){
  const folder=`data/local/bundles/${run.bundle_id}`;
  const manifest=JSON.parse(await readFile(`${folder}/manifest.json`,'utf8'));
  const page=await browser.newPage();
  await page.route('**/?sandy-validation',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><title>Sandy numerical validation</title>'}));
  await page.route('**/validation-array/*',async route=>{
   const name=new URL(route.request().url()).pathname.split('/').at(-1);
   if(!['z','solid'].includes(name))throw Error('Unexpected array');
   await route.fulfill({body:await readFile(`${folder}/${name}.bin`)});
  });
  await page.exposeFunction('recordProgress',async progress=>{
   await writeFile(`${root}/progress.json`,JSON.stringify({grid:run.grid_cells,...progress}));
   console.log(JSON.stringify({grid:run.grid_cells,...progress}));
  });
  await page.goto('http://127.0.0.1:5173/?sandy-validation');
  console.log('Starting unchanged production GPUSolver:',run.grid_cells);
  const result=await page.evaluate(async({run,manifest,protocol})=>{
   const {GPUSolver,inputIdentity,coastalInitialDepth}=await import('/src/testing/gpu-harness.ts');
   const [zBytes,solidBytes]=await Promise.all(['z','solid'].map(async name=>(await fetch('/validation-array/'+name)).arrayBuffer()));
   const nx=manifest.grid.nx,ny=manifest.grid.ny,n=nx*ny;
   const solid=new Uint8Array(solidBytes),cells=Array.from({length:ny},(_,y)=>y*nx).filter(i=>!solid[i]);
   const input={nx,ny,dx:manifest.grid.dx_m,dy:manifest.grid.dy_m,z:new Float32Array(zBytes),solid,rainWeights:new Float32Array(n),roughness:new Float32Array(n).fill(protocol.roughness),capacity:new Float32Array(n),infiltration:new Float32Array(n),spatialOrder:2,maxStepS:protocol.max_step_s,coastal:{edge:'west',cells,levels:run.levels,datum:'NAVD88 minus '+manifest.grid.elevation_origin_m+' m',source:protocol.forcing}};
   input.depth=coastalInitialDepth(input,input.coastal);
   const identity=await inputIdentity(input),solver=new GPUSolver(input),started=performance.now(),frames=[];
   let next=0,lastProgress=started;
   try{
    while(solver.time<protocol.duration_s-1e-7){
     const stop=Math.min(protocol.duration_s,next);
     if(solver.time>=stop-1e-7){
      const f=solver.frame();frames.push({time_s:f.time_s,depth:Array.from(f.depth),maxDepth:Array.from(f.maxDepth),ledger:f.ledger});
      next+=protocol.duration_s/120;
     }
     const target=Math.min(protocol.duration_s,next);
     for(let batch=0;batch<100&&solver.time<target-1e-7;batch++)solver.step(Math.min(protocol.max_step_s,target-solver.time),0);
     if(performance.now()-lastProgress>10000){lastProgress=performance.now();await window.recordProgress({simulatedHours:solver.time/3600,wallSeconds:(performance.now()-started)/1000,steps:solver.steps});}
     await new Promise(resolve=>setTimeout(resolve,0));
    }
    const f=solver.frame();frames.push({time_s:f.time_s,depth:Array.from(f.depth),maxDepth:Array.from(f.maxDepth),ledger:f.ledger});
    return {bundle_id:run.bundle_id,grid:manifest.grid,inputHash:identity,renderer:solver.info(),elapsedMs:performance.now()-started,steps:f.steps,ledger:f.ledger,frames,coastal:input.coastal};
   }finally{solver.dispose();}
  },{run,manifest,protocol});
  await writeFile(`${root}/simulation-${run.grid_cells}.json`,JSON.stringify(result));
  console.log('Completed',run.grid_cells,JSON.stringify({wallSeconds:result.elapsedMs/1000,steps:result.steps,ledger:result.ledger}));
  await page.close();
 }
}finally{await browser.close();}
