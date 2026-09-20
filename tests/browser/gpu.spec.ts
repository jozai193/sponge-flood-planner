import {test,expect} from '@playwright/test';
test('second-order closed walls retain rainfall around all four excavated corners',async({page})=>{
 await page.goto('/');
 const results=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);const results=[];
  for(const corner of [0,3,12,15]){
   const z=new Float32Array(16);z[corner]=-.1;
   const input={nx:4,ny:4,dx:1,dy:1,z,solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16).fill(.03),capacity:new Float32Array(16),infiltration:new Float32Array(16),spatialOrder:2,maxStepS:.02};
   const solver=new GPUSolver(input);
   while(solver.time<2-1e-7){const end=solver.time<1-1e-7?1:2;solver.step(Math.min(.02,end-solver.time),end===1?.2:0);}
   results.push(solver.frame().ledger);solver.dispose();
  }return results;
 });
 for(const ledger of results){expect(Math.abs(ledger.stored_m3-3.2)).toBeLessThan(.00001);expect(ledger.outflow_m3).toBe(0);expect(ledger.relative_residual).toBeLessThan(.00001);}
});
test('full GPU checkpoint resumes identically and rejects stale or corrupted state',async({page})=>{
 await page.goto('/');const result=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);const n=16;
  const input={nx:4,ny:4,dx:2,dy:3,spatialOrder:2,z:new Float32Array(n),solid:new Uint8Array(n),rainWeights:new Float32Array(n).fill(1),roughness:new Float32Array(n).fill(.03),capacity:new Float32Array(n).fill(.05),infiltration:new Float32Array(n).fill(.001),percolation:new Float32Array(n).fill(.0001),depth:Float32Array.from({length:n},(_,i)=>i<8?.1:.02),maxStepS:.1,
   facilityLinks:[{cell:0,targetCell:15,reservoir:'subsurface',crestDepthM:0,ratePerS:.1,maxFlowM3S:.01,source:'checkpoint fixture'}]};
  const run=(s:any,end:number)=>{while(s.time<end-1e-7)s.step(Math.min(.1,end-s.time),.001);};
  const original=new GPUSolver(input);run(original,1);const checkpoint=await original.checkpoint();run(original,2);const expected=original.frame();original.dispose();
  const resumed=new GPUSolver(input);await resumed.restore(checkpoint);run(resumed,2);const actual=resumed.frame();
  let invalid=false;try{await resumed.restore({...checkpoint,state:new Float32Array(1)});}catch{invalid=true;}
  const preserved=resumed.frame().time_s===2||Math.abs(resumed.frame().time_s-2)<1e-7;resumed.dispose();
  const stale=new GPUSolver({...input,maxStepS:.2});let mismatch=false;try{await stale.restore(checkpoint);}catch{mismatch=true;}stale.dispose();
  return {depthError:Math.max(...actual.depth.map((v:number,i:number)=>Math.abs(v-expected.depth[i]))),soilError:Math.max(...actual.subsurfaceDepth.map((v:number,i:number)=>Math.abs(v-expected.subsurfaceDepth[i]))),ledger:actual.ledger,expectedLedger:expected.ledger,invalid,preserved,mismatch};
 });
 expect(result.depthError).toBe(0);expect(result.soilError).toBe(0);expect(result.ledger).toEqual(result.expectedLedger);expect(result.invalid&&result.preserved&&result.mismatch).toBe(true);
});
test('coupled nonlinear ratings converge against float64 reference with receiver tailwater',async({page})=>{
 await page.goto('/');const results=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver,exchangeFacilities}=await import(path);
  const solid=new Uint8Array(16).fill(1);solid[0]=solid[15]=0;const depth=new Float32Array(16);depth[0]=.5;depth[15]=.1;
  const base={nx:4,ny:4,dx:10,dy:10,z:new Float32Array(16),solid,rainWeights:new Float32Array(16),roughness:new Float32Array(16),capacity:new Float32Array(16),infiltration:new Float32Array(16),depth};
  return [{kind:'orifice',areaM2:.5,coefficient:.6},{kind:'weir',widthM:2,coefficient:1.7}].map(rating=>{
   const link={cell:0,targetCell:15,reservoir:'surface',crestDepthM:0,ratePerS:0,maxFlowM3S:100,source:'coupled convergence',rating};
   let reference=Float64Array.from(depth);const soil=new Float64Array(16);
   for(let i=0;i<4000;i++)reference=exchangeFacilities(reference,soil,base.z,100,[link],.001).depth;
   return [.8,.4,.2].map(maxStepS=>{
    const solver=new GPUSolver({...base,maxStepS,facilityLinks:[link]});while(solver.time<4-1e-7)solver.step(Math.min(maxStepS,4-solver.time),0);const f=solver.frame();solver.dispose();
    return {error:Math.abs(f.depth[0]-reference[0]),returned:f.depth[15],residual:f.ledger.relative_residual,outflow:f.ledger.outflow_m3};
   });
  });
 });
 for(const runs of results){expect(runs[1].error).toBeLessThan(runs[0].error*.7);expect(runs[2].error).toBeLessThan(runs[1].error*.7);for(const run of runs){expect(run.returned).toBeGreaterThan(.1);expect(run.residual).toBeLessThan(.00001);expect(run.outflow).toBe(0);}}
});
test('nonlinear GPU outlet and spillway converge to analytic recession as timestep shrinks',async({page},testInfo)=>{
 await page.goto('/');const results=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);
  const solid=new Uint8Array(16).fill(1);solid[0]=0;const depth=new Float32Array(16);depth[0]=.5;
  const base={nx:4,ny:4,dx:10,dy:10,z:new Float32Array(16),solid,rainWeights:new Float32Array(16),roughness:new Float32Array(16),capacity:new Float32Array(16),infiltration:new Float32Array(16),depth};
  return [{kind:'orifice',areaM2:.5,coefficient:.6},{kind:'weir',widthM:2,coefficient:1.7}].map(rating=>{
   const k=rating.kind==='orifice'?.6*.5*Math.sqrt(2*9.80665)/100:1.7*2/100;
   const exact=rating.kind==='orifice'?(Math.sqrt(.5)-k*4/2)**2:(1/Math.sqrt(.5)+k*4/2)**-2;
   const runs=[.8,.4,.2].map(maxStepS=>{
    const solver=new GPUSolver({...base,maxStepS,facilityLinks:[{cell:0,targetCell:null,reservoir:'surface',crestDepthM:0,ratePerS:0,maxFlowM3S:100,source:'analytical recession',rating}]});
    while(solver.time<4-1e-7)solver.step(Math.min(maxStepS,4-solver.time),0);const f=solver.frame();solver.dispose();return {maxStepS,depth:f.depth[0],error:Math.abs(f.depth[0]-exact),residual:f.ledger.relative_residual};
   });return {kind:rating.kind,exact,runs};
  });
 });
 for(const r of results){expect(r.runs[1].error).toBeLessThan(r.runs[0].error*.65);expect(r.runs[2].error).toBeLessThan(r.runs[1].error*.65);expect(r.runs[2].error).toBeLessThan(.0003);for(const run of r.runs)expect(run.residual).toBeLessThan(.00001);}
 await testInfo.attach('nonlinear-convergence.json',{body:JSON.stringify(results,null,2),contentType:'application/json'});
 console.log('Nonlinear convergence '+JSON.stringify(results));
});
test('all four facilities complete saturated before/after runs with conserved storage and explicit returns',async({page},testInfo)=>{
 await page.goto('/');const results=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver,compileDesign}=await import(path);const n=16;
  const solid=new Uint8Array(n).fill(1);for(const i of [0,2,15])solid[i]=0;
  const z=new Float32Array(n);z[15]=-1;
  const rainWeights=new Float32Array(n);rainWeights[0]=rainWeights[2]=1;
  const depth=new Float32Array(n);depth[0]=depth[2]=.02;
  const input={nx:4,ny:4,dx:2,dy:3,z,solid,rainWeights,roughness:new Float32Array(n),capacity:new Float32Array(n),infiltration:new Float32Array(n),depth};
  const run=(data:any)=>{const s=new GPUSolver(data);while(s.time<4-1e-7)s.step(Math.min(.1,4-s.time),s.time<2-1e-7?.005:0);const f=s.frame();s.dispose();return {donorDepth:f.depth[0],receiverDepth:f.depth[15],storage:f.subsurfaceDepth[0],ledger:f.ledger};};
  const baseline=run(input);
  return ['rain_garden','bioswale','permeable_pavement','detention_basin'].map(kind=>{
   const basin=kind==='detention_basin';
   const design={id:kind,kind,cells:[0,2],eligibility:'user_assumed',excavationM:kind==='permeable_pavement'?0:.2,storageDepthM:basin?0:.001,conductivityMS:.001,percolationMS:0,roughness:.1,costMinor:0,parameterSource:'Synthetic isolated storage fixture',swaleSlope:kind==='bioswale'?.01:0,cloggingFraction:kind==='permeable_pavement'?.5:0,
    surfaceControl:{targetCell:15,crestDepthM:.01,ratePerS:.5,maxFlowM3S:.006},underdrain:basin?undefined:{targetCell:15,crestDepthM:0,ratePerS:.5,maxFlowM3S:.0006}};
   return {kind,baseline,planned:run(compileDesign(input,[design],0))};
  });
 });
 for(const r of results){expect(r.planned.ledger.relative_residual).toBeLessThan(.00001);expect(r.planned.ledger.outflow_m3).toBe(0);expect(r.planned.receiverDepth).toBeGreaterThan(r.baseline.receiverDepth);expect(r.planned.donorDepth).toBeLessThan(r.baseline.donorDepth);expect(r.planned.storage).toBeLessThanOrEqual(.001001);if(r.kind==='detention_basin')expect(r.planned.storage).toBe(0);else expect(r.planned.storage).toBeGreaterThan(0);}
 await testInfo.attach('four-facility-water-balance.json',{body:JSON.stringify(results,null,2),contentType:'application/json'});
});
test('GPU underdrains return water to a shared surface receiver with analytic recession and a closed ledger',async({page})=>{
 await page.goto('/');const result=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);const n=16;
  const solid=new Uint8Array(n).fill(1);for(const i of [0,2,15])solid[i]=0;
  const capacity=new Float32Array(n);capacity[0]=capacity[2]=.1;
  const input={nx:4,ny:4,dx:2,dy:3,z:new Float32Array(n),solid,rainWeights:new Float32Array(n),roughness:new Float32Array(n),capacity,infiltration:new Float32Array(n),saturation:1,
   facilityLinks:[0,2].map(cell=>({cell,targetCell:15,reservoir:'subsurface',crestDepthM:.02,ratePerS:.2,maxFlowM3S:10,source:'isolated analytical underdrains'}))};
  const solver=new GPUSolver(input);while(solver.time<2-1e-7)solver.step(Math.min(.1,2-solver.time),0);const f=solver.frame();solver.dispose();
  const external=new GPUSolver({...input,facilityLinks:input.facilityLinks.map(link=>({...link,targetCell:null}))});while(external.time<2-1e-7)external.step(Math.min(.1,2-external.time),0);const e=external.frame();external.dispose();
  return {storage:f.subsurfaceDepth[0],returned:f.depth[15],ledger:f.ledger,external:e.ledger};
 });
 const release=.08*(1-Math.exp(-.4));expect(result.storage).toBeCloseTo(.1-release,6);expect(result.returned).toBeCloseTo(2*release,6);
 expect(result.ledger.outflow_m3).toBe(0);expect(result.ledger.relative_residual).toBeLessThan(.00001);
 expect(result.external.outflow_m3).toBeCloseTo(12*release,5);expect(result.external.relative_residual).toBeLessThan(.00001);
});

test('GPU facility surface outlet stops at high receiving water and routes capacity-limited overflow',async({page})=>{
 await page.goto('/');const result=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);const n=16;
  const solid=new Uint8Array(n).fill(1);solid[0]=solid[15]=0;
  const depth=new Float32Array(n);depth[0]=.5;depth[15]=.6;
  const input={nx:4,ny:4,dx:2,dy:3,z:new Float32Array(n),solid,rainWeights:new Float32Array(n),roughness:new Float32Array(n),capacity:new Float32Array(n),infiltration:new Float32Array(n),depth,
   facilityLinks:[{cell:0,targetCell:15,reservoir:'surface',crestDepthM:.1,ratePerS:100,maxFlowM3S:.006,source:'capacity and tailwater fixture'}]};
  const blocked=new GPUSolver(input);blocked.step(.1,0);const b=blocked.frame();blocked.dispose();
  depth[15]=0;const solver=new GPUSolver(input);while(solver.time<1-1e-7)solver.step(Math.min(.1,1-solver.time),0);const f=solver.frame();solver.dispose();return {blocked:b.depth[0],donor:f.depth[0],receiver:f.depth[15],ledger:f.ledger};
 });
 expect(result.blocked).toBeCloseTo(.5,6);expect(result.donor).toBeCloseTo(.499,6);expect(result.receiver).toBeCloseTo(.001,6);expect(result.ledger.outflow_m3).toBe(0);expect(result.ledger.relative_residual).toBeLessThan(.00001);
});
test('imported rainfall integrates across dry gaps on GPU',async({page})=>{
 await page.goto('/');
 const result=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {simulate}=await import(path);const n=16;
  const input={nx:4,ny:4,dx:1,dy:1,z:new Float32Array(n),solid:new Uint8Array(n),rainWeights:new Float32Array(n).fill(1),roughness:new Float32Array(n),capacity:new Float32Array(n),infiltration:new Float32Array(n)};
  const frame=await simulate(input,{duration:10,recession:2,depth:.003,intervals:[{start_s:2,end_s:5,rate_m_s:.001}]},new AbortController().signal);
  return {depth:frame.depth[0],ledger:frame.ledger};
 });
 expect(result.depth).toBeCloseTo(.003,6);expect(result.ledger.rain_m3).toBeCloseTo(.048,5);expect(result.ledger.relative_residual).toBeLessThan(.001);
});
import {readFileSync} from 'node:fs';
const fixture=JSON.parse(readFileSync('tests/fixtures/cpu-dam-break.json','utf8'));
const order2Fixtures=JSON.parse(readFileSync('tests/fixtures/cpu-order2.json','utf8'));
test('second-order GPU agrees with CPU over lake, smooth terrain wave and dry front',async({page})=>{
 await page.goto('/');const results=await page.evaluate(async(cases)=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);
  return cases.map((data:any)=>{
   const count=data.nx*data.ny;const s=new GPUSolver({nx:data.nx,ny:data.ny,dx:1,dy:1,spatialOrder:2,z:new Float32Array(data.z),depth:new Float32Array(data.initial),solid:new Uint8Array(count),rainWeights:new Float32Array(count).fill(1),roughness:new Float32Array(count),capacity:new Float32Array(count),infiltration:new Float32Array(count)});
   while(s.time<data.end_s-1e-7)s.step(data.end_s-s.time,0);const f=s.frame();s.dispose();return {name:data.name,rmse:Math.sqrt(f.depth.reduce((sum:number,h:number,i:number)=>sum+(h-data.depth[i])**2,0)/count),residual:f.ledger.relative_residual,maxSpeed:Math.max(...f.velocityX.map((v:number,i:number)=>Math.hypot(v,f.velocityY[i])))};
  });
 },order2Fixtures);
 console.log('Order 2 parity '+JSON.stringify(results));
 for(const r of results){expect(r.rmse).toBeLessThan(.001);expect(r.residual).toBeLessThan(.001);if(r.name==='lake')expect(r.maxSpeed).toBeLessThan(.00001);}
});
test('physics planner completes budgeted search and records aligned baseline and planned storms',async({page})=>{
 await page.goto('/');
 const result=await page.evaluate(async()=>{
  return await new Promise<any>((resolve,reject)=>{
   const worker=new Worker('/@fs/E:/Nextstep%20Hacks%20hackathon/packages/simulation/src/planner-worker.ts',{type:'module'});
   const frames:{baseline:number[];planned:number[]}={baseline:[],planned:[]};let plan:any;
   const timeout=setTimeout(()=>{worker.terminate();reject(new Error('Planner timeout'));},60000);
   worker.onerror=e=>{clearTimeout(timeout);worker.terminate();reject(new Error(e.message));};
   worker.onmessage=e=>{const d=e.data;if(d.type==='PLAN')plan=d.result;if(d.type==='REPLAY')frames[d.side as 'baseline'|'planned'].push(d.frame.time_s);
    if(d.type==='ERROR'){clearTimeout(timeout);worker.terminate();reject(new Error(d.error));}
    if(d.type==='COMPLETE'){clearTimeout(timeout);worker.terminate();resolve({frames,plan,baselineScore:d.baselineScore,plannedScore:d.plannedScore});}
   };
   const count=16;
   worker.postMessage({mode:'PLAN',runId:'test',budgetMinor:100,storm:{duration:1,recession:0,depth:.02},input:{nx:4,ny:4,dx:1,dy:1,z:new Float32Array(count),solid:new Uint8Array(count),rainWeights:new Float32Array(count).fill(1),roughness:new Float32Array(count),infiltration:new Float32Array(count),capacity:new Float32Array(count)},designs:[{id:'site',kind:'permeable_pavement',cells:[0],eligibility:'user_assumed',excavationM:0,storageDepthM:.1,conductivityMS:.001,percolationMS:0,roughness:.03,costMinor:100,parameterSource:'test fixture',surfaceControl:{targetCell:null,crestDepthM:0,ratePerS:0,maxFlowM3S:.1,rating:{kind:'orifice',areaM2:.0001,coefficient:.6}}}]});
  });
 });
 expect(result.plan.evaluations).toBe(2);expect(result.plan.selected).toEqual([]);
 expect(result.frames.baseline).toHaveLength(121);expect(result.frames.planned).toEqual(result.frames.baseline);
 expect(result.frames.baseline[120]).toBeCloseTo(1);expect(result.baselineScore).toBe(0);expect(result.plannedScore).toBe(0);
});
test('finite intervention storage saturates and conserves water',async({page})=>{
 await page.goto('/');const result=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver,compileDesign}=await import(path);const n=8,count=64;
  const base={nx:n,ny:n,dx:1,dy:1,z:new Float32Array(count),solid:new Uint8Array(count),rainWeights:new Float32Array(count).fill(1),roughness:new Float32Array(count),infiltration:new Float32Array(count),capacity:new Float32Array(count),depth:new Float32Array(count).fill(.02)};
  const design={id:'test',kind:'permeable_pavement',cells:Array.from({length:count},(_,i)=>i),eligibility:'user_assumed',excavationM:0,storageDepthM:.005,conductivityMS:.001,percolationMS:0,roughness:.03,costMinor:0,parameterSource:'Controlled finite-reservoir test'};
  const solver=new GPUSolver(compileDesign(base,[design],0));while(solver.time<20)solver.step(Math.min(1,20-solver.time),0);const frame=solver.frame();solver.dispose();return {depth:frame.depth[0],residual:frame.ledger.relative_residual};
 });expect(result.depth).toBeCloseTo(.015,5);expect(result.residual).toBeLessThan(.001);
});
test('GPU dam break matches CPU reference and rejects invalid inputs',async({page})=>{
 await page.goto('/');const result=await page.evaluate(async(data)=>{
  const modulePath='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(modulePath);const n=data.nx;
  const input={nx:n,ny:n,dx:1,dy:1,z:new Float32Array(n*n),solid:new Uint8Array(n*n),rainWeights:new Float32Array(n*n).fill(1),roughness:new Float32Array(n*n),infiltration:new Float32Array(n*n),capacity:new Float32Array(n*n),depth:new Float32Array(data.initial)};
  let rejected=false;try{new GPUSolver({...input,dx:NaN});}catch{rejected=true;}
  const solver=new GPUSolver(input);while(solver.time<data.end_s-1e-8)solver.step(data.end_s-solver.time,0);const f=solver.frame();solver.dispose();
  const rmse=Math.sqrt(data.depth.reduce((s:number,h:number,i:number)=>s+(h-f.depth[i])**2,0)/data.depth.length);return {rmse,residual:f.ledger.relative_residual,rejected};
 },fixture);expect(result.rejected).toBe(true);expect(result.rmse).toBeLessThan(.001);expect(result.residual).toBeLessThan(.001);
});
test('GPU HLL conserves rain and preserves still water',async({page})=>{
  await page.goto('/');
  const result=await page.evaluate(async()=>{
    const modulePath='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(modulePath);
    const n=16,count=n*n,z=new Float32Array(count),ones=new Float32Array(count).fill(1),zeros=new Float32Array(count);
    const input={nx:n,ny:n,dx:2,dy:2,z,solid:new Uint8Array(count),rainWeights:ones,roughness:zeros,infiltration:zeros,capacity:zeros};
    const solver=new GPUSolver(input);for(let i=0;i<100;i++){const dt=Math.min(solver.stableDt(),100-solver.time);solver.step(dt,.0001);}
    const rain=solver.frame(),info=solver.info();solver.dispose();
    for(let y=0;y<n;y++)for(let x=0;x<n;x++)z[y*n+x]=.2*Math.exp(-((x-8)**2+(y-8)**2)/20);
    const lake=new GPUSolver({...input,z,depth:Float32Array.from(z,v=>1-v)});
    while(lake.time<2){lake.step(Math.min(lake.stableDt(),2-lake.time),0);}
    const frame=lake.frame();const drift=Math.max(...Array.from(frame.depth as Float32Array,(h,i)=>Math.abs(h+z[i]-1)));lake.dispose();
    return {info,rainDepth:rain.depth[0],rainResidual:rain.ledger.relative_residual,drift};
  });
  console.log(JSON.stringify(result));
  expect(result.rainDepth).toBeCloseTo(.01,5);
  expect(result.rainResidual).toBeLessThan(.001);
  expect(result.drift).toBeLessThan(.0001);
});

test('GPU outlet matches analytic reservoir drainage and accounts for exported water',async({page})=>{
 await page.goto('/');const result=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);const n=16;
  const solver=new GPUSolver({nx:4,ny:4,dx:2,dy:3,z:new Float32Array(n),solid:new Uint8Array(n),rainWeights:new Float32Array(n).fill(1),roughness:new Float32Array(n),infiltration:new Float32Array(n),capacity:new Float32Array(n),depth:new Float32Array(n).fill(.5),outlets:Array.from({length:n},(_,cell)=>({cell,crestDepthM:.1,ratePerS:.2,maxFlowM3S:100,source:'analytic test'}))});
  while(solver.time<2-1e-7)solver.step(Math.min(.1,2-solver.time),0);const f=solver.frame();solver.dispose();return {h:f.depth[0],ledger:f.ledger};
 });expect(result.h).toBeCloseTo(.1+.4*Math.exp(-.4),5);expect(result.ledger.outflow_m3).toBeGreaterThan(0);expect(result.ledger.relative_residual).toBeLessThan(.00001);
});

test('external inflow honours start and stop times and downstream head blocks drainage',async({page})=>{
 await page.goto('/');const r=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);const n=16;
  const input={nx:4,ny:4,dx:1,dy:1,z:new Float32Array(n),solid:new Uint8Array(n),rainWeights:new Float32Array(n).fill(1),roughness:new Float32Array(n),capacity:new Float32Array(n),infiltration:new Float32Array(n),inflows:Array.from({length:n},(_,cell)=>({cell,flowM3S:.01,startS:.5,endS:1.5,source:'mass accounting fixture'})),outlets:Array.from({length:n},(_,cell)=>({cell,crestDepthM:0,ratePerS:100,maxFlowM3S:100,tailwaterElevationM:1,source:'high tailwater fixture'}))};
  const s=new GPUSolver(input);while(s.time<2-1e-7)s.step(Math.min(.3,2-s.time),0);const f=s.frame();s.dispose();return {h:f.depth[0],ledger:f.ledger};
 });expect(r.h).toBeCloseTo(.01,5);expect(r.ledger.inflow_m3).toBeCloseTo(.16,6);expect(r.ledger.rain_m3).toBe(0);expect(r.ledger.outflow_m3).toBe(0);expect(r.ledger.relative_residual).toBeLessThan(.00001);
});


test('lost GPU context rejects further computation and a fresh context resumes the saved state',async({page})=>{
 await page.goto('/');
 const result=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);
  const input={nx:4,ny:4,dx:2,dy:2,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16).fill(.03),capacity:new Float32Array(16).fill(.05),infiltration:new Float32Array(16).fill(.001),maxStepS:.1};
  const original=new GPUSolver(input);original.step(.1,.001);const checkpoint=await original.checkpoint();
  original.step(.1,.001);const expected=original.frame();
  const extension=original.gl.getExtension('WEBGL_lose_context');if(!extension)throw new Error('Context-loss test extension unavailable');
  extension.loseContext();await new Promise(r=>setTimeout(r,0));
  let stepRejected=false,checkpointRejected=false;
  try{original.step(.1,.001);}catch(e){stepRejected=String(e).includes('context lost');}
  try{await original.checkpoint();}catch(e){checkpointRejected=String(e).includes('lost GPU context');}
  const fresh=new GPUSolver(input);await fresh.restore(checkpoint);fresh.step(.1,.001);const actual=fresh.frame();
  fresh.dispose();original.dispose();
  return {stepRejected,checkpointRejected,sameDepth:actual.depth.every((h:number,i:number)=>h===expected.depth[i]),sameLedger:JSON.stringify(actual.ledger)===JSON.stringify(expected.ledger)};
 });
 expect(result).toEqual({stepRejected:true,checkpointRejected:true,sameDepth:true,sameLedger:true});
});


test('coastal reservoir conserves water at every edge and resumes with its exchange ledger',async({page})=>{
 await page.goto('/');
 const results=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);const results=[];
  for(const edge of ['west','east','south','north'])for(const level of [.5,1,1.5]){
   const cells=Array.from({length:16},(_,i)=>i).filter(i=>edge==='west'?i%4===0:edge==='east'?i%4===3:edge==='south'?i<4:i>=12);
   const input={nx:4,ny:4,dx:2,dy:3,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16),roughness:new Float32Array(16),capacity:new Float32Array(16),infiltration:new Float32Array(16),depth:new Float32Array(16).fill(1),spatialOrder:2,maxStepS:.02,coastal:{edge,cells,levels:[{timeS:0,elevationM:level}],source:'analytic reservoir test',datum:'local bed zero'}};
   const solver=new GPUSolver(input);while(solver.time<.5-1e-7)solver.step(Math.min(.02,.5-solver.time),0);
   const checkpoint=await solver.checkpoint();while(solver.time<1-1e-7)solver.step(Math.min(.02,1-solver.time),0);const expected=solver.frame();solver.dispose();
   const resumed=new GPUSolver(input);await resumed.restore(checkpoint);while(resumed.time<1-1e-7)resumed.step(Math.min(.02,1-resumed.time),0);const actual=resumed.frame();resumed.dispose();
   results.push({edge,level,ledger:actual.ledger,error:Math.max(...actual.depth.map((v:number,i:number)=>Math.abs(v-expected.depth[i])))});
  }return results;
 });
 for(const r of results){expect(r.error).toBe(0);expect(r.ledger.relative_residual).toBeLessThan(.00001);if(r.level===1){expect(r.ledger.inflow_m3).toBe(0);expect(r.ledger.outflow_m3).toBe(0);}else if(r.level>1)expect(r.ledger.inflow_m3).toBeGreaterThan(0);else expect(r.ledger.outflow_m3).toBeGreaterThan(0);}
});


test('rising coastal level wets dry land without crossing a solid barrier',async({page})=>{
 await page.goto('/');const result=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);const nx=16,ny=4,n=nx*ny,solid=new Uint8Array(n);for(let y=0;y<ny;y++)solid[y*nx+8]=1;
  const input={nx,ny,dx:1,dy:1,z:new Float32Array(n),solid,rainWeights:new Float32Array(n),roughness:new Float32Array(n).fill(.03),capacity:new Float32Array(n),infiltration:new Float32Array(n),spatialOrder:2,maxStepS:5,coastal:{edge:'west',cells:[0,16,32,48],levels:[{timeS:0,elevationM:0},{timeS:2,elevationM:1},{timeS:4,elevationM:0}],source:'dry barrier test',datum:'local zero'}};
  const solver=new GPUSolver(input);while(solver.time<8-1e-7)solver.step(Math.min(5,8-solver.time),0);const frame=solver.frame();solver.dispose();
  return {ledger:frame.ledger,wet:frame.maxDepth[3],beyond:[...frame.maxDepth].filter((_,i)=>i%nx>=8),minimum:Math.min(...frame.depth)};
 });
 expect(result.ledger.relative_residual).toBeLessThan(.00001);expect(result.wet).toBeGreaterThan(.01);expect(result.beyond.every(v=>v===0)).toBe(true);expect(result.minimum).toBeGreaterThanOrEqual(0);expect(result.ledger.inflow_m3).toBeGreaterThan(0);expect(result.ledger.outflow_m3).toBeGreaterThan(0);
});


test('small-amplitude coastal wave approaches the independent linear shallow-water solution under refinement',async({page})=>{
 await page.goto('/');const results=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);const results=[],amplitude=.002,omega=Math.PI/2,c=Math.sqrt(9.80665),end=8;
  for(const nx of [100,200,400]){
   const ny=4,n=nx*ny,dx=100/nx,levels=Array.from({length:161},(_,i)=>({timeS:i*.05,elevationM:1+amplitude*Math.sin(omega*i*.05)}));
   const input={nx,ny,dx,dy:1,z:new Float32Array(n),solid:new Uint8Array(n),rainWeights:new Float32Array(n),roughness:new Float32Array(n),capacity:new Float32Array(n),infiltration:new Float32Array(n),depth:new Float32Array(n).fill(1),spatialOrder:2,maxStepS:.1,coastal:{edge:'west',cells:[0,nx,2*nx,3*nx],levels,source:'linear wave benchmark',datum:'flat bed zero'}};
   const solver=new GPUSolver(input);const started=performance.now();while(solver.time<end-1e-7)solver.step(Math.min(.1,end-solver.time),0);const frame=solver.frame();let error=0;
   for(let x=0;x<nx;x++){const delay=end-(x+.5)*dx/c,exact=1+(delay>0?amplitude*Math.sin(omega*delay):0);error+=(frame.depth[x]-exact)**2;}
   results.push({nx,rmse:Math.sqrt(error/nx),residual:frame.ledger.relative_residual,wallMs:performance.now()-started,steps:frame.steps,renderer:solver.info().renderer});solver.dispose();
  }return results;
 });
 console.log('Coastal linear-wave refinement',JSON.stringify(results));expect(results[2].rmse).toBeLessThan(results[0].rmse*.8);expect(results[2].rmse).toBeLessThan(.0003);for(const r of results)expect(r.residual).toBeLessThan(.00001);
});
