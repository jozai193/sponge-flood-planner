import type {CoastalBoundary} from '../simulation/src/coastal';
import {validateGPUInput,type GPUInput,type Inflow,type Outlet} from '../simulation/src/gpu';
import {validateRainfall,type StormRun,type RainInterval} from '../simulation/src/rainfall';
import {scenarioSpec,assessScenario,sameScenarioValue} from './scenario-wire';

/** Versioned forcing composition; domain/array identity remains inputIdentity v6. */
export type ForcingComponents={rainfall:boolean;external:boolean;coastal:boolean};
export type FloodConfiguration={mode:'rain'|'external'|'compound'|'coastal'|'combined';
 components?:ForcingComponents;coastal?:CoastalBoundary;inflows:Inflow[];outlets:Outlet[];source:string};
export type ScenarioForcingV2={version:2;components:ForcingComponents;storm:StormRun;
 coastal?:CoastalBoundary;inflows:Inflow[];outlets:Outlet[]};

export function forcingComponents(flood:FloodConfiguration):ForcingComponents{
 switch(flood.mode){
  case 'rain':return {rainfall:true,external:false,coastal:false};
  case 'external':return {rainfall:false,external:true,coastal:false};
  case 'compound':return {rainfall:true,external:true,coastal:false};
  case 'coastal':return {rainfall:false,external:false,coastal:true};
  case 'combined':
   if(flood.components&&['rainfall','external','coastal'].every(k=>typeof flood.components![k as keyof ForcingComponents]==='boolean'))return {...flood.components};
   throw new Error('Combined scenario needs explicit rainfall, inflow and coastal selections');
  default:throw new Error('Unsupported flood scenario');
 }
}

export function composeForcing(flood:FloodConfiguration,rain:{depthMm:number;durationS:number;recessionS:number;intervals?:RainInterval[];
 name?:string;returnPeriodYears?:number|null;sourceIds?:string[];distribution?:string;antecedentSaturation?:number;evidence?:StormRun['evidence']}):ScenarioForcingV2{
 const components=forcingComponents(flood),coastal=components.coastal?flood.coastal:undefined;
 const inflows=components.external?flood.inflows:[];
 // Preserve every legacy preset clock exactly. For composed runs, extending
 // the coastal tail extends recession, never the rainfall duration/rate.
 const coastEnd=Math.max(1,coastal?.levels.at(-1)?.timeS??600);
 const duration=flood.mode==='coastal'?coastEnd:rain.durationS;
 let end=Math.max(duration+(flood.mode==='coastal'?600:rain.recessionS),...inflows.map(f=>f.endS));
 if(flood.mode==='combined'&&components.coastal)end=Math.max(end,coastEnd+600);
 const storm:StormRun={duration,recession:end-duration,depth:components.rainfall?rain.depthMm/1000:0,
  intervals:components.rainfall?rain.intervals:undefined,...(components.rainfall?{
   name:rain.name,returnPeriodYears:rain.returnPeriodYears,sourceIds:rain.sourceIds,
   distribution:rain.distribution,antecedentSaturation:rain.antecedentSaturation,evidence:rain.evidence}: {})};
 return {version:2,components,storm,coastal,inflows,outlets:flood.outlets};
}

/** Draft controls may be incomplete; call at execution, never while rendering. */
export function validateScenarioExecution(input:GPUInput,forcing:ScenarioForcingV2){
 if(forcing.version!==2)throw new Error('Unsupported forcing composition version');
 const c=forcing.components;
 if(!c.rainfall&&!c.external&&!c.coastal)throw new Error('Enable at least one flood source');
 if(c.coastal&&!forcing.coastal)throw new Error('Apply a coastal boundary first');
 if(c.external&&!forcing.inflows.length)throw new Error('Apply an external inflow first');
 if(!sameScenarioValue(input.coastal??null,forcing.coastal??null)||
    !sameScenarioValue(input.inflows??[],forcing.inflows)||
    !sameScenarioValue(input.outlets??[],forcing.outlets))throw new Error('Compiled input does not match the selected flood sources');
 if(c.coastal&&c.external){
  const boundary=new Set(forcing.coastal!.cells);
  if(forcing.inflows.some(i=>boundary.has(i.cell)))throw new Error('External inflow overlaps the coastal boundary. Choose separate edges to avoid counting the same boundary source twice.');
 }
 validateRainfall(forcing.storm);validateGPUInput(input);
 const assessment=assessScenario(scenarioSpec(input,forcing));
 if(!assessment.compatible)throw new Error(assessment.reasons.join(' '));
}
