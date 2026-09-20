async page => {
 await page.evaluate(async()=>{
  const id='2c607f51e1a064fc76ee6f5585cbc343358d0e9a39ead1a2806643e21cae37ba';
  const bundle=await (await fetch('/api/v1/bundles/'+id)).json();
  const context=await (await fetch('/api/v1/bundles/'+id+'/context')).json();
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

 });
 await page.reload();
}
