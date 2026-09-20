async page => {
 const panel=page.getByRole('region',{name:'Scenario data suitability'});
 await panel.waitFor();
 if(!(await panel.innerText()).includes('Data gaps'))throw Error('Missing suitability panel');
 if(!await panel.locator('details').getAttribute('open').then(v=>v!==null))await panel.locator('summary').click();
 if(!(await panel.innerText()).includes('Download timestamps'))throw Error('Terrain age explanation missing');
 const mode=page.getByRole('combobox',{name:'Flood scenario',exact:true});
 await mode.selectOption('coastal');
 if(!(await panel.innerText()).includes('Complete the flood setup'))throw Error('Missing-source state not shown');
 await mode.selectOption('rain');
 const result=await page.evaluate(async()=>{
  const root='/@fs/E:/Nextstep Hacks hackathon/';
  const {assessScenarioData}=await import(root+'packages/domain/data-admission.ts');
  const {scenarioSpec,sameScenarioValue}=await import(root+'packages/domain/scenario-wire.ts');
  const cases=await (await fetch(root+'packages/contracts/fixtures/data-admission-cases.json')).json();
  const python=await (await fetch(root+'artifacts/verification/data-admission-v1/python-results.json')).json();
  for(let i=0;i<cases.length;i++)if(!sameScenarioValue(assessScenarioData(cases[i].scenario,cases[i].manifest),python[i]))throw Error('Cross-language mismatch: '+cases[i].name);
  const session=await (await fetch('/api/v1/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
  const headers={'Content-Type':'application/json',Authorization:'Bearer '+session.token};
  const bundleId='42005ef908cf047c50e6ef57a95d6bc689ea0f230455d92acae28226632e470b';
  const response=await fetch('/api/v1/bundles/'+bundleId,{headers});if(!response.ok)throw Error('Shared sample unavailable');
  const bundle=await response.json();
  const spec=structuredClone(cases.find(c=>c.name==='rainfall does not require bathymetry').scenario);
  spec.domain={nx:bundle.grid.nx,ny:bundle.grid.ny,dx_m:bundle.grid.dx_m,dy_m:bundle.grid.dy_m,horizontal_crs:bundle.grid.crs,vertical_datum:bundle.grid.vertical_datum??'unspecified',elevation_origin_m:bundle.grid.elevation_origin_m??null,bundle_id:bundleId};
  const assessment=await (await fetch('/api/v1/scenarios/assess-data',{method:'POST',headers,body:JSON.stringify(spec)})).json();
  if(!sameScenarioValue(assessment.data,assessScenarioData(spec,bundle)))throw Error('Live API differs from browser');
  const wrong={...spec,domain:{...spec.domain,dx_m:spec.domain.dx_m+1}};
  const mismatch=await (await fetch('/api/v1/scenarios/assess-data',{method:'POST',headers,body:JSON.stringify(wrong)})).json();
  if(mismatch.data.exploratory_allowed)throw Error('Server admitted mismatched grid');
  const inaccessible=await fetch('/api/v1/scenarios/assess-data',{method:'POST',headers,body:JSON.stringify({...spec,domain:{...spec.domain,bundle_id:'f'.repeat(64)}})});
  if(inaccessible.status!==404)throw Error('Missing bundle access check');
  const {simulate,buildReport,inputIdentity}=await import('/src/testing/gpu-harness.ts');
  const input={nx:4,ny:4,dx:1,dy:1,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16),capacity:new Float32Array(16),infiltration:new Float32Array(16),maxStepS:10,spatialOrder:2};
  const storm={duration:1,recession:1,depth:.2},frames=[];
  const final=await simulate(input,storm,new AbortController().signal,frame=>frames.push(frame)),hash=await inputIdentity(input);
  const provenance={bundle_id:'controlled-data-screen',grid:{nx:4,ny:4,dx_m:1,dy_m:1,crs:'LOCAL_METRES'},sources:[],quality:{},buildings:[]};
  const envelope=scenarioSpec(input,{version:2,components:{rainfall:true,external:false,coastal:false},storm,inflows:[],outlets:[]},{bundleId:provenance.bundle_id,inputHash:hash});
  const score=final.maxDepth.reduce((sum,h)=>sum+Math.max(0,h-.1),0);
  const comparison={baselineScore:score,plannedScore:score,designs:[],evidence:{storm,scenario:envelope,maxStepS:10,baselineInputHash:hash,plannedInputHash:hash,assessmentExcludedCells:[],budgetMinor:0,engine:'webgl2-hll-order2'}};
  const request={input,plannedInput:input,baseline:frames,planned:frames,result:comparison,provenance};
  const report=await buildReport(request);
  if(report.scenario.dataAssessment.status!=='needs_data'||!report.html.includes('Scenario data suitability')||!report.html.includes('Download timestamps'))throw Error('Data gaps missing from exports');
  let rejected=false;try{await buildReport({...request,provenance:{...provenance,bundle_id:'wrong'}});}catch{rejected=true;}
  if(!rejected)throw Error('Mismatched export provenance admitted');
  return {sharedCases:cases.length,liveBundle:bundleId,liveAssessment:assessment.data,wrongGridBlocked:true,missingBundleStatus:inaccessible.status,exportIncludesDataGaps:true,wrongExportProvenanceRejected:true};
 });
 return {...result,uiPanel:true,incompleteCoastalSetupExplained:true,rainfallRestored:true};
}
