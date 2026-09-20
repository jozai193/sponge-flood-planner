import {simulate,floodScore,type StormRun} from './experiment';
import {compileDesign,type PhysicalDesign} from '../../domain/interventions';
import type {GPUInput} from './gpu';
import {search,type SearchResult} from '../../optimizer';
import {inputIdentity} from './identity';
import {validateRainfall} from './rainfall';
let controller:AbortController|undefined;
self.onmessage=async(event:MessageEvent)=>{
  if(event.data.type==='CANCEL'){controller?.abort();return;}
  if(controller)return;
  const {input:rawInput,designs,budgetMinor,storm,stormEnsemble,runId,mode}=event.data as {input:GPUInput;designs:PhysicalDesign[];budgetMinor:number;currency?:string;storm:StormRun;stormEnsemble?:StormRun[];runId:string;mode:'PLAN'|'COMPARE'};
  const currency=event.data.currency??'USD';
  const ensemble=mode==='PLAN'?(stormEnsemble?.length?stormEnsemble:[storm]):[storm];for(const member of ensemble)validateRainfall(member);
  const input={...rawInput,maxStepS:Math.min(rawInput.maxStepS??10,designs.some(d=>d.surfaceControl?.rating)?.2:10)};
  controller=new AbortController();const signal=controller.signal;
  const send=(type:string,data:object={})=>self.postMessage({type,runId,...data});
  try{
    if(!/^[A-Z]{3}$/.test(currency))throw new Error('Invalid planning currency');
    if(designs.some(d=>d.costBreakdown&&d.costBreakdown.currency!==currency))throw new Error('Design cost currency does not match planning currency');
    if(new Set(designs.map(d=>d.id)).size!==designs.length)throw new Error('Duplicate candidate IDs');
    for(const d of designs)compileDesign(input,[d],Number.MAX_SAFE_INTEGER);
    const excluded=new Set(designs.flatMap(d=>d.cells));
    let selected=designs.filter(d=>d.planningConstraint!=='excluded'),searchResult:SearchResult|undefined;
    if(mode==='PLAN'){
      const catalog=designs.map(d=>({id:d.id,costMinor:d.costMinor,conflicts:designs.filter(other=>other.id!==d.id&&other.cells.some(c=>d.cells.includes(c))).map(other=>other.id)}));
      let evaluations=0;
      const result=await search(catalog,async ids=>{
        send('PROGRESS',{message:`Evaluating plan ${++evaluations} (up to 24 alternatives × ${ensemble.length} identical sensitivity storms)`});
        const compiled=compileDesign(input,designs.filter(d=>ids.includes(d.id)),budgetMinor),scores=[];
        for(const member of ensemble){const frame=await simulate(compiled,member,signal);scores.push(floodScore(frame,input,excluded));}
        return Math.max(...scores);
      },{budgetMinor,locked:designs.filter(d=>d.planningConstraint==='locked').map(d=>d.id),excluded:designs.filter(d=>d.planningConstraint==='excluded').map(d=>d.id),maxEvaluations:24,signal});
      signal.throwIfAborted();searchResult=result;selected=designs.filter(d=>result.selected.includes(d.id));send('PLAN',{result,designs:selected});
    }
    const planned=compileDesign(input,selected,budgetMinor);
    send('PROGRESS',{message:'Recording baseline replay'});
    const baseline=await simulate(input,storm,signal,frame=>send('REPLAY',{side:'baseline',frame}));
    send('PROGRESS',{message:'Recording planned replay'});
    const after=await simulate(planned,storm,signal,frame=>send('REPLAY',{side:'planned',frame}));
    const robustBaseline=searchResult?.evaluated.find(item=>item.selected.length===0)?.score,robustPlanned=searchResult?.score;
    send('COMPLETE',{baselineScore:floodScore(baseline,input,excluded),plannedScore:floodScore(after,input,excluded),designs:selected,evidence:{schemaVersion:3,runId,maxStepS:input.maxStepS,facilityModel:'Linear, orifice or sharp-crested weir surface controls; resolved surface overtopping; free underdrains without pressure or backflow',baselineFacilityLinks:input.facilityLinks??[],plannedFacilityLinks:planned.facilityLinks??[],createdAt:new Date().toISOString(),engine:'webgl2-hll-order'+(input.spatialOrder??1),forcing:{coastal:input.coastal??null,inflows:input.inflows??[],outlets:input.outlets??[]},mode,storm,robustPlanning:mode==='PLAN'?{aggregation:'worst_case_peak_excess_depth',members:ensemble.map(s=>({depth:s.depth,duration:s.duration,recession:s.recession,sensitivity_factor:(s as StormRun&{sensitivity_factor?:number}).sensitivity_factor??1})),baselineScore:robustBaseline??null,plannedScore:robustPlanned??null,noBenefit:robustBaseline!==undefined&&robustPlanned!==undefined&&robustPlanned>=robustBaseline}:null,budgetMinor,currency,searchResult,baselineInputHash:await inputIdentity({...input,maxStepS:input.maxStepS??10}),plannedInputHash:await inputIdentity({...planned,maxStepS:planned.maxStepS??10}),candidateDesigns:designs,assessmentExcludedCells:[...excluded].sort((a,b)=>a-b),objective:'Worst-case across the disclosed rainfall depth sensitivity ensemble of sum of peak excess depth above 0.1 m times cell area outside fixed candidate, solid and permanent-water masks',baselineLedger:baseline.ledger,plannedLedger:after.ledger,initialSoilCondition:'Same fractional saturation; different facility capacities can change initial stored soil water',validation:'Screening model, not site-calibrated; passing conservation does not establish flood accuracy. Rainfall sensitivity members are not probabilities.'}});
  }catch(error){send(signal.aborted?'CANCELLED':'ERROR',{error:signal.aborted?undefined:String(error)});}
  finally{controller=undefined;}
};
