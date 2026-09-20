async page => {
 return await page.evaluate(async()=>{
  const {GPUSolver,buildReport,unpackInput}=await import('/src/testing/gpu-harness.ts');
  const {composeForcing,validateScenarioExecution}=await import('/@fs/E:/Nextstep Hacks hackathon/packages/domain/scenario.ts');
  const {scenarioInput}=await import('/src/scenario-input.ts');
  const {rainfallAt}=await import('/@fs/E:/Nextstep Hacks hackathon/packages/simulation/src/rainfall.ts');
  const reference=await (await fetch('/@fs/E:/Nextstep Hacks hackathon/artifacts/verification/scenario-composition-v1/cpu-reference.json')).json();
  const results=[];
  for(const expected of reference){
   const base={nx:4,ny:4,dx:2,dy:3,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16).fill(.03),capacity:new Float32Array(16),infiltration:new Float32Array(16),spatialOrder:2,maxStepS:.05};
   const flood={mode:'combined',components:{rainfall:expected.rain,external:expected.inflow,coastal:true},coastal:{edge:'west',cells:[0,4,8,12],levels:[{timeS:0,elevationM:.2},{timeS:5,elevationM:.4},{timeS:10,elevationM:.2},{timeS:20,elevationM:.2}],source:'controlled composition test',datum:'local metres'},inflows:[{cell:15,flowM3S:.01,startS:0,endS:10,source:'controlled inflow'}],outlets:[],source:'fixture'};
   const forcing=composeForcing(flood,{depthMm:2.5,durationS:5,recessionS:15}),input=scenarioInput(base,flood,null);
   validateScenarioExecution(input,forcing);
   const solver=new GPUSolver(input);
   const advance=(s,end)=>{while(s.time<end-1e-7){const r=rainfallAt(forcing.storm,s.time);s.step(Math.min(.05,end-s.time,r.knot-s.time),r.rate);}};
   advance(solver,10);const checkpoint=await solver.checkpoint();advance(solver,20);const frame=solver.frame();solver.dispose();
   const resumed=new GPUSolver(input);await resumed.restore(checkpoint);advance(resumed,20);const replay=resumed.frame();resumed.dispose();
   const maxError=Math.max(...frame.depth.map((v,i)=>Math.abs(v-expected.depth[i])));
   if(maxError>2e-5||frame.ledger.relative_residual>1e-5||Math.abs(frame.ledger.rain_m3-(expected.rain?.24:0))>1e-6)throw Error('Combined source parity or ledger failed: '+JSON.stringify({maxError,ledger:frame.ledger}));
   if(frame.depth.some((v,i)=>v!==replay.depth[i]))throw Error('Combined restart differs');
   results.push({rain:expected.rain,inflow:expected.inflow,maxDepthErrorM:maxError,ledger:frame.ledger,exactRestart:true});
  }
  // Exercise the actual planner worker and the portable export, with all sources.
  const base={nx:4,ny:4,dx:2,dy:3,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16).fill(.03),capacity:new Float32Array(16),infiltration:new Float32Array(16),spatialOrder:2,maxStepS:.5};
  const flood={mode:'combined',components:{rainfall:true,external:true,coastal:true},coastal:{edge:'west',cells:[0,4,8,12],levels:[{timeS:0,elevationM:.2},{timeS:5,elevationM:.21},{timeS:10,elevationM:.2}],source:'controlled planner boundary',datum:'local metres'},inflows:[{cell:15,flowM3S:.001,startS:0,endS:10,source:'controlled planner inflow'}],outlets:[],source:'fixture'};
  const forcing=composeForcing(flood,{depthMm:2.5,durationS:5,recessionS:15}),input=scenarioInput(base,flood,null);
  const before=[],after=[];
  const result=await new Promise((resolve,reject)=>{
   const w=new Worker('/@fs/E:/Nextstep Hacks hackathon/packages/simulation/src/planner-worker.ts',{type:'module'});
   const timeout=setTimeout(()=>{w.terminate();reject(Error('Planner timeout'));},60000);
   w.onmessage=({data:d})=>{if(d.type==='REPLAY')(d.side==='baseline'?before:after).push(d.frame);if(d.type==='COMPLETE'||d.type==='ERROR'){clearTimeout(timeout);w.terminate();d.type==='COMPLETE'?resolve(d):reject(Error(d.error));}};
   w.onerror=e=>{clearTimeout(timeout);w.terminate();reject(Error(e.message));};
   w.postMessage({mode:'COMPARE',runId:'composed-verification',input,designs:[],budgetMinor:0,storm:forcing.storm});
  });
  const {scenarioSpec}=await import('/@fs/E:/Nextstep Hacks hackathon/packages/domain/scenario-wire.ts');
  result.evidence.scenario=scenarioSpec(input,forcing,{inputHash:result.evidence.baselineInputHash});
  const session=await (await fetch('/api/v1/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
  const assessmentResponse=await fetch('/api/v1/scenarios/assess',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+session.token},body:JSON.stringify(result.evidence.scenario)});
  const assessment=await assessmentResponse.json();
  if(!assessmentResponse.ok||!assessment.compatible||assessment.data_validation!=='not_assessed')throw Error('Live server assessment failed');
  const plannedInput={...input,percolation:new Float32Array(16)};
  const report=await buildReport({input,plannedInput,baseline:before,planned:after,result,provenance:{label:'Controlled combined sources',buildings:[],sources:[],grid:{nx:4,ny:4,dx_m:2,dy_m:3}}});
  if(!report.scenario.evidence.scenario)throw Error('Envelope missing from export');
  let tamperedRejected=false;
  try{await buildReport({input,plannedInput,baseline:before,planned:after,result:{...result,evidence:{...result.evidence,scenario:{...result.evidence.scenario,forcing:{...result.evidence.scenario.forcing,storm:{duration:5,recession:605,depth:.1,intervals:null}}}}},provenance:{buildings:[]}});}catch{tamperedRejected=true;}
  if(!tamperedRejected)throw Error('Tampered storm envelope accepted');
  const exported=unpackInput(report.scenario.baselineInput);
  if(!exported.coastal||exported.inflows.length!==1||report.scenario.evidence.storm.depth!==.0025||before.length!==121||after.length!==121)throw Error('Export lost forcing or replay');
  const final=before.at(-1);
  if(Math.abs(final.ledger.rain_m3-.24)>1e-6)throw Error('Planner diluted rain');
  return {liveAssessment:assessment,exportEnvelope:true,tamperedRejected,controlledGpuCases:results,planner:{frames:before.length,endS:final.time_s,rainM3:final.ledger.rain_m3,allSourcesInExport:true,identicalZeroDesign:before.every((f,i)=>f.depth.every((v,j)=>v===after[i].depth[j]))}};
 });
}
