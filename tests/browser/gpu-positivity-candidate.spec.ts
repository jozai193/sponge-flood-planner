import {test,expect} from '@playwright/test';

test('candidate migrates tiny negatives with an explicit ledger and versioned resume',async({page})=>{
  await page.goto('/?positivity-fixture');
  const result=await page.evaluate(async()=>{
    const originalPath='/@fs/E:/Nextstep Hacks hackathon/packages/simulation/src/gpu.ts';
    const candidatePath='/@fs/E:/Nextstep Hacks hackathon/packages/simulation/src/gpu-positivity-candidate.ts';
    const {GPUSolver:Original}=await import(originalPath),{GPUSolver:Candidate}=await import(candidatePath);
    const n=16,solid=new Uint8Array(n).fill(1);solid[0]=solid[15]=0;
    const depth=new Float32Array(n);depth[15]=.1;
    const input={nx:4,ny:4,dx:1,dy:1,z:new Float32Array(n),solid,depth,rainWeights:new Float32Array(n),roughness:new Float32Array(n),capacity:new Float32Array(n),infiltration:new Float32Array(n),spatialOrder:2,maxStepS:.1};
    const original=new Original(input),candidate=new Candidate(input),resumed=new Candidate(input);
    try{
      const baseline=await original.checkpoint();baseline.state[0]=-5e-12;
      await original.restore(baseline);const migration=await candidate.importBaselineCheckpoint(baseline);
      const before=candidate.frame(),versioned=await candidate.checkpoint();
      await resumed.restore(versioned);candidate.step(.1,0);resumed.step(.1,0);original.step(.1,0);
      const expected=candidate.frame(),actual=resumed.frame();
      let legacyRejects=false,materialRejected=false,overBudgetRejected=false;
      try{await original.restore(versioned);}catch{legacyRejects=true;}
      const bad={...baseline,state:baseline.state.slice()};bad.state[0]=-2e-10;
      try{await candidate.importBaselineCheckpoint(bad);}catch{materialRejected=true;}
      try{await resumed.restore({...versioned,roundoffVolume:1});}catch{overBudgetRejected=true;}
      return {migration,baselineUnchanged:baseline.state[0]<0,originalDepth:original.frame().depth[0],candidateDepth:expected.depth[0],beforeLedger:before.ledger,version:versioned.version,
        equalDepth:actual.depth.every((v:number,i:number)=>v===expected.depth[i]),equalLedger:JSON.stringify(actual.ledger)===JSON.stringify(expected.ledger),legacyRejects,materialRejected,overBudgetRejected};
    }finally{original.dispose();candidate.dispose();resumed.dispose();}
  });
  expect(result.baselineUnchanged).toBe(true);expect(result.originalDepth).toBeLessThan(0);expect(result.candidateDepth).toBe(0);
  expect(result.beforeLedger.roundoff_correction_m3).toBe(result.migration.volumeM3);
  expect(result.version).toBe(2);expect(result.equalDepth&&result.equalLedger&&result.legacyRejects&&result.materialRejected&&result.overBudgetRejected).toBe(true);
});

test('candidate rolls back real corrections when a later source stage rejects the attempt',async({page})=>{
  await page.goto('/?positivity-fixture');
  const result=await page.evaluate(async()=>{
    const path='/@fs/E:/Nextstep Hacks hackathon/packages/simulation/src/gpu-positivity-candidate.ts';const {GPUSolver}=await import(path);
    const n=16,solid=new Uint8Array(n).fill(1);solid[0]=solid[15]=0;const depth=new Float32Array(n);depth[15]=.1;
    const solver=new GPUSolver({nx:4,ny:4,dx:1,dy:1,z:new Float32Array(n),solid,depth,rainWeights:new Float32Array(n),roughness:new Float32Array(n),capacity:new Float32Array(n),infiltration:new Float32Array(n),spatialOrder:2,maxStepS:.1});
    try{
      const stage=solver.stage.bind(solver),sources=solver.sources.bind(solver);let sourcesCount=0;const seen:number[]=[];
      solver.stage=(...args:any[])=>{const result=stage(...args);if(args[4]===1){
        const state=solver.read(args[1]);state[0]=-5e-12;const gl=solver.gl;gl.bindTexture(gl.TEXTURE_2D,args[1].handle);gl.texSubImage2D(gl.TEXTURE_2D,0,0,0,4,4,gl.RGBA,gl.FLOAT,state);
      }return result;};
      solver.sources=(...args:any[])=>{sourcesCount++;if(sourcesCount===2){seen.push(solver.roundoffVolume);throw new Error('NUMERICAL_INVALID: injected post-correction failure');}return sources(...args);};
      solver.step(.1,0);const f=solver.frame();return {retries:solver.retries,seen,correction:f.ledger.roundoff_correction_m3,depth:f.depth[0],time:f.time_s};
    }finally{solver.dispose();}
  });
  expect(result.retries).toBe(1);expect(result.seen[0]).toBeGreaterThan(0);expect(result.correction).toBe(result.seen[0]);expect(result.depth).toBe(0);expect(result.time).toBe(.05);
});
