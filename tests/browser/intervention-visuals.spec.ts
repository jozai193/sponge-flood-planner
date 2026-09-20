import {test,expect} from '@playwright/test';

test('all four interventions make modelled flood-reduction mechanisms visible',async({page})=>{
 await page.goto('/?intro=0');
 await page.evaluate(async()=>{
  const harnessPath='/src/testing/gpu-harness.ts',storagePath='/src/completed-comparison.ts';
  const harness=await import(harnessPath),storage=await import(storagePath);
  const n=64,input={nx:8,ny:8,dx:2,dy:2,z:new Float32Array(n),solid:new Uint8Array(n),rainWeights:new Float32Array(n).fill(1),roughness:new Float32Array(n).fill(.03),capacity:new Float32Array(n),infiltration:new Float32Array(n),percolation:new Float32Array(n),maxStepS:.1,spatialOrder:2};
  const shared={eligibility:'user_assumed' as const,conductivityMS:20/3_600_000,percolationMS:5/3_600_000,costMinor:10000,parameterSource:'Controlled browser visualization fixture'};
  const designs=[
   {...shared,id:'visible-rain-garden',kind:'rain_garden' as const,cells:[9,10],excavationM:.15,storageDepthM:.15,roughness:.1,underdrain:{targetCell:null,crestDepthM:0,ratePerS:.1,maxFlowM3S:.01}},
   {...shared,id:'visible-bioswale',kind:'bioswale' as const,cells:[13,14],excavationM:.2,storageDepthM:.15,roughness:.1,swaleSlope:.01,swaleAxis:'x' as const,surfaceControl:{targetCell:15,crestDepthM:.1,ratePerS:.1,maxFlowM3S:.01}},
   {...shared,id:'visible-pavement',kind:'permeable_pavement' as const,cells:[49,50],excavationM:0,storageDepthM:.15,roughness:.03,cloggingFraction:.25,underdrain:{targetCell:51,crestDepthM:0,ratePerS:.1,maxFlowM3S:.01}},
   {...shared,id:'visible-basin',kind:'detention_basin' as const,cells:[53,54],excavationM:.2,storageDepthM:0,roughness:.1,surfaceControl:{targetCell:null,crestDepthM:.1,ratePerS:.1,maxFlowM3S:.01}},
  ];
  const budgetMinor=40000,plannedInput=harness.compileDesign(input,designs,budgetMinor),storm={duration:1,recession:2,depth:.2},baseline:any[]=[],planned:any[]=[];
  const before=await harness.simulate(input,storm,new AbortController().signal,(frame:any)=>baseline.push(frame));
  const after=await harness.simulate(plannedInput,storm,new AbortController().signal,(frame:any)=>planned.push(frame));
  const excluded=new Set(designs.flatMap(design=>design.cells)),score=(frame:any)=>frame.maxDepth.reduce((sum:number,depth:number,cell:number)=>sum+(excluded.has(cell)?0:Math.max(0,depth-.1))*input.dx*input.dy,0);
  const baselineInputHash=await harness.inputIdentity(input),plannedInputHash=await harness.inputIdentity(plannedInput);
  const result={baselineScore:score(before),plannedScore:score(after),designs,evidence:{storm,maxStepS:.1,baselineInputHash,plannedInputHash,assessmentExcludedCells:[...excluded],budgetMinor,engine:'webgl2-hll-order2',createdAt:'2026-09-20',baselineLedger:before.ledger,plannedLedger:after.ledger}};
  const bundle={bundle_id:'controlled-intervention-visuals',extent_m:16,buildings:[],candidates:[],quality:{},grid:{nx:8,ny:8,dx_m:2,dy_m:2,origin_x_m:0,origin_y_m:0,crs:'LOCAL',row_direction:'north'},label:'Controlled intervention visualization',assumptions:['Synthetic browser visualization fixture.']};
  const report={input,plannedInput,baseline,planned,result,provenance:bundle};
  await storage.saveCompletedComparison({version:1,savedAt:new Date().toISOString(),report,context:{bundle,input,designs,flood:{mode:'rain',inflows:[],outlets:[],source:''},rain:200,minutes:1/60,importedStorm:{name:'Controlled storm',duration_s:1,recession_s:2,depth_m:.2},budget:400,city:null,contextStatus:'Controlled fixture'}});
 });
 await page.reload();
 await page.getByRole('button',{name:'Restore saved comparison',exact:true}).click();
 const replay=page.getByRole('dialog',{name:'Storm comparison'});
 await expect(replay).toBeVisible({timeout:30000});
 await expect(replay.getByLabel('Modelled intervention effects at replay time')).toContainText('than baseline at the same cells');
 const status=replay.getByLabel('Selected intervention status');
 for(const name of ['Rain garden · visible-rain-garden','Bioswale · visible-bioswale','Permeable pavement · visible-pavement','Detention basin · visible-basin'])await expect(status).toContainText(name);
 await expect(replay.getByText('Highlighted footprints',{exact:false})).toBeVisible();
 await expect(replay.getByText('Down arrows appear only where surface water and configured infiltration coexist',{exact:false})).toBeVisible();
 const slider=replay.getByRole('slider',{name:'Replay time'}),maximum=await slider.getAttribute('max');
 if(!maximum)throw new Error('Replay maximum is unavailable');
 await slider.fill(maximum);
 await expect(replay.getByLabel('Selected intervention status')).toContainText(/m³ at its footprint/);
 await replay.screenshot({path:'output/playwright/intervention-effects-comparison.png'});
});
