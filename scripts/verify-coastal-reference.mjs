import {chromium} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
const mode=process.argv[2]??'nvidia';
const candidate=process.argv.includes('--positivity-candidate');
const output=process.argv.find(a=>a.startsWith('--output='))?.slice('--output='.length);
if(candidate&&!output)throw Error('Candidate reference verification requires a separate --output= path');
if(!['nvidia','software'].includes(mode))throw Error('Choose nvidia or software');
const root='artifacts/validation/coastal-reference';
const fixture=JSON.parse(await readFile(`${root}/float64.json`,'utf8'));
const browser=await chromium.launch(mode==='nvidia'?{channel:'chrome'}:{args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const page=await browser.newPage();
 await page.route('**/?coastal-reference',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><title>Coastal reference verification</title>'}));
 await page.goto('http://127.0.0.1:5173/?coastal-reference');
 const results=await page.evaluate(async ({fixture,candidate})=>{
  const {GPUSolver}=await import(candidate?'/@fs/E:/Nextstep Hacks hackathon/packages/simulation/src/gpu-positivity-candidate.ts':'/src/testing/gpu-harness.ts');
  const results=[];
  for(const c of fixture.cases){
   const n=(c.nx??4)*(c.ny??4);
   const input={nx:c.nx??4,ny:c.ny??4,dx:c.dx??2,dy:c.dy??2,z:new Float32Array(c.z??n),solid:new Uint8Array(c.solid??n),
    roughness:new Float32Array(n).fill(.035),rainWeights:new Float32Array(n),capacity:new Float32Array(n),infiltration:new Float32Array(n),
    depth:c.initial?new Float32Array(c.initial):new Float32Array(n).fill(.2),spatialOrder:2,maxStepS:c.max_step_s,
    coastal:{edge:c.edge,cells:c.cells,levels:c.levels,datum:'local metres',source:'analytic verification fixture'}};
   const solver=new GPUSolver(input);
   try{
    while(solver.time<c.duration_s-1e-7)solver.step(Math.min(c.max_step_s,c.duration_s-solver.time),0);
    const f=solver.frame();
    results.push({edge:c.edge,case_name:c.case_name??c.edge,renderer:solver.info(),
     max_depth_error_m:Math.max(...f.depth.map((h,i)=>Math.abs(h-c.depth[i]))),
     max_peak_error_m:Math.max(...f.maxDepth.map((h,i)=>Math.abs(h-c.maxDepth[i]))),
     inflow_error_m3:Math.abs(f.ledger.inflow_m3-c.ledger.inflow_m3),
     outflow_error_m3:Math.abs(f.ledger.outflow_m3-c.ledger.outflow_m3),ledger:f.ledger});
   }finally{solver.dispose();}
  }
  return results;
 },{fixture,candidate});
 const passed=results.every(r=>r.max_depth_error_m<.0001&&r.max_peak_error_m<.0001&&r.inflow_error_m3<.001&&r.outflow_error_m3<.001&&r.ledger.relative_residual<.00001);
 await writeFile(output??`${root}/${mode}.json`,JSON.stringify({passed,candidate,results,limitation:fixture.limitation},null,2),output?{flag:'wx'}:undefined);
 console.log(JSON.stringify({passed,results}));
 if(!passed)throw Error('GPU/coastal float64 comparison failed');
}finally{await browser.close();}
