async page => {
 const result=await page.evaluate(async()=>{
  const {unpackInput}=await import('/@fs/E:/Nextstep%20Hacks%20hackathon/packages/metrics/report.ts');
  const {simulate,inputIdentity}=await import('/src/testing/gpu-harness.ts');
  const url='/@fs/E:/Nextstep%20Hacks%20hackathon/artifacts/verification/stabilization-v1/export-set/sponge-reproducible-comparison.json';
  const scenario=await (await fetch(url)).json();
  const results=[];
  for(const side of ['baseline','planned']){
   const input=unpackInput(scenario[side+'Input']);
   if(await inputIdentity(input)!==scenario.evidence[side+'InputHash'])throw Error('Exported input identity mismatch');
   const frame=await simulate(input,scenario.evidence.storm,new AbortController().signal);
   const saved=scenario.outputs[side+'Final'];
   const depthError=Math.max(...frame.depth.map((h,i)=>Math.abs(h-saved.depth[i])));
   const peakError=Math.max(...frame.maxDepth.map((h,i)=>Math.abs(h-saved.maxDepth[i])));
   if(Math.max(depthError,peakError)>1e-5)throw Error('Export rerun differs beyond 0.01 mm');
   results.push({side,depthErrorM:depthError,peakErrorM:peakError,massResidual:frame.ledger.relative_residual});
  }
  return {results,storm:scenario.evidence.storm,bundle:scenario.provenance.bundle_id,validation:scenario.validation};
 });
 return result;
}
