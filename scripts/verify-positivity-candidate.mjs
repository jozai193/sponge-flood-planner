/** Bounded, separately recorded continuation of the rejected Sandy checkpoint.
 * Never rewrites an existing replay, protocol, checkpoint, or verification output.
 */
import {chromium} from '@playwright/test';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root='artifacts/validation/sandy-2012-grid128';
const output=process.argv[2];if(!output)throw Error('Pass a new output JSON path');
const sha=value=>createHash('sha256').update(value).digest('hex');
const frozenPaths=[`${root}/checkpoint-128.json`,`${root}/simulation-128.json`,`${root}/protocol.json`,'packages/simulation/src/gpu.ts','apps/web/src/testing/gpu-harness.ts'];
const before=Object.fromEntries(await Promise.all(frozenPaths.map(async p=>[p,sha(await readFile(p))])));
const envelope=JSON.parse(await readFile(`${root}/checkpoint-128.json`,'utf8'));
if(sha(envelope.payload)!==envelope.sha256)throw Error('Checkpoint checksum mismatch');
const {checkpoint}=JSON.parse(envelope.payload);
const protocol=JSON.parse(await readFile(`${root}/protocol.json`,'utf8')),run=protocol.bundles[0];
const folder=`data/local/bundles/${run.bundle_id}`,manifest=JSON.parse(await readFile(`${folder}/manifest.json`,'utf8'));
if(checkpoint.time!==64260)throw Error('Expected the 17.85 h checkpoint; refusing an unplanned continuation');
const browser=await chromium.launch({channel:'chrome'});let result;
try{
  const page=await browser.newPage();await page.route('**/?positivity-validation',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><title>Experimental positivity validation</title>'}));
  await page.route('**/positivity-array/*',async route=>{
    const name=new URL(route.request().url()).pathname.split('/').at(-1);if(!['z','solid'].includes(name))throw Error('Unexpected array');
    await route.fulfill({body:await readFile(`${folder}/${name}.bin`)});
  });
  await page.goto('http://127.0.0.1:5173/?positivity-validation');
  result=await page.evaluate(async({checkpoint,protocol,run,manifest})=>{
    const {GPUSolver:Original,coastalInitialDepth}=await import('/src/testing/gpu-harness.ts');
    const {GPUSolver:Candidate}=await import('/@fs/E:/Nextstep Hacks hackathon/packages/simulation/src/gpu-positivity-candidate.ts');
    const [zb,sb]=await Promise.all(['z','solid'].map(async name=>(await fetch('/positivity-array/'+name)).arrayBuffer()));
    const {nx,ny,dx_m:dx,dy_m:dy}=manifest.grid,n=nx*ny,solid=new Uint8Array(sb),edge=protocol.boundary_edge??'west';
    const cells=Array.from({length:n},(_,i)=>i).filter(i=>!solid[i]&&(edge==='west'?i%nx===0:edge==='east'?i%nx===nx-1:edge==='south'?i<nx:i>=n-nx));
    const input={nx,ny,dx,dy,z:new Float32Array(zb),solid,rainWeights:new Float32Array(n),roughness:new Float32Array(n).fill(protocol.roughness),capacity:new Float32Array(n),infiltration:new Float32Array(n),spatialOrder:2,maxStepS:protocol.max_step_s,
      coastal:{edge,cells,levels:run.levels,datum:'NAVD88 minus '+manifest.grid.elevation_origin_m+' m',source:protocol.forcing}};
    input.depth=coastalInitialDepth(input,input.coastal);
    const baseline={...checkpoint,state:new Float32Array(checkpoint.state),history:new Float32Array(checkpoint.history)};
    const runs={};let migration=null;
    for(const [name,Solver] of [['original',Original],['candidate',Candidate]]){
      const solver=new Solver(input),started=performance.now();
      try{
        if(name==='original')await solver.restore(baseline);else migration=await solver.importBaselineCheckpoint(baseline);
        const before=solver.frame();let error=null;
        try{while(solver.time<protocol.duration_s-1e-7){
          for(let batch=0;batch<100&&solver.time<protocol.duration_s-1e-7;batch++)solver.step(Math.min(protocol.max_step_s,protocol.duration_s-solver.time),0);
          await new Promise(r=>setTimeout(r,0));
        }}catch(e){error=String(e);}
        const frame=solver.frame(),cp=await solver.checkpoint();
        let resumeEqual=null;if(name==='candidate'){
          const resumed=new Candidate(input);try{await resumed.restore(cp);const restored=resumed.frame();resumeEqual=restored.depth.every((v,i)=>v===frame.depth[i])&&JSON.stringify(restored.ledger)===JSON.stringify(frame.ledger);}finally{resumed.dispose();}
        }
        runs[name]={fromTimeS:before.time_s,toTimeS:frame.time_s,steps:solver.steps-checkpoint.steps,retries:solver.retries-checkpoint.retries,error,wallSeconds:(performance.now()-started)/1000,renderer:solver.info(),
          initialNegativeCells:Array.from(before.depth).filter(v=>v<0).length,negativeCells:Array.from(frame.depth).filter(v=>v<0).length,minDepthM:Math.min(...frame.depth),ledger:frame.ledger,resumeEqual,depth:Array.from(frame.depth),maxDepth:Array.from(frame.maxDepth)};
      }finally{solver.dispose();}
    }
    const maximumDifference=key=>Math.max(...runs.original[key].map((v,i)=>Math.abs(v-runs.candidate[key][i])));
    const comparison={maxDepthDifferenceM:maximumDifference('depth'),maxPeakDepthDifferenceM:maximumDifference('maxDepth')};
    for(const run of Object.values(runs)){delete run.depth;delete run.maxDepth;}
    return {migration,runs,comparison};
  },{checkpoint,protocol,run,manifest});
}finally{await browser.close();}
for(const [p,hash] of Object.entries(before))if(sha(await readFile(p))!==hash)throw Error('Frozen file changed: '+p);
const software=Object.fromEntries(await Promise.all(['packages/simulation/src/gpu-positivity-candidate.ts','packages/simulation/src/positivity-roundoff.ts','scripts/verify-positivity-candidate.mjs'].map(async p=>[p,sha(await readFile(p))])));
await mkdir(new URL('../artifacts/verification/',import.meta.url),{recursive:true});
await writeFile(output,JSON.stringify({createdAt:new Date().toISOString(),scope:'Experimental 9-minute tail continuation from rejected Sandy checkpoint; not a repaired historical accuracy result or a full-event rerun.',productionEnabled:false,frozenSha256:before,candidateSoftwareSha256:software,...result},null,2),{flag:'wx'});
console.log(JSON.stringify(result,null,2));
