import {test,expect} from 'vitest';
import {composeForcing,forcingComponents,validateScenarioExecution,type FloodConfiguration} from '../../packages/domain/scenario';
import {scenarioInput} from '../../apps/web/src/scenario-input';
import {coastalInitialDepth,type CoastalBoundary} from '../../packages/simulation/src/coastal';
import {inputIdentity} from '../../packages/simulation/src/identity';
import {rainfallAt} from '../../packages/simulation/src/rainfall';
import type {GPUInput} from '../../packages/simulation/src/gpu';

const boundary:CoastalBoundary={edge:'west',cells:[0,4,8,12],levels:[{timeS:0,elevationM:.2},{timeS:180,elevationM:.4},{timeS:1200,elevationM:.2}],source:'test assumed levels',datum:'local metres'};
const base:GPUInput={nx:4,ny:4,dx:2,dy:3,z:new Float32Array(16),solid:new Uint8Array(16),roughness:new Float32Array(16).fill(.03),rainWeights:new Float32Array(16).fill(1),capacity:new Float32Array(16),infiltration:new Float32Array(16)};
const config: FloodConfiguration={mode:'rain',coastal:boundary,inflows:[{cell:15,flowM3S:.001,startS:0,endS:2400,source:'assumed test inflow'}],outlets:[],source:'fixture'};
const rain={depthMm:10,durationS:60,recessionS:30,intervals:[{start_s:0,end_s:20,rate_m_s:.0005}]};

test.each(['rain','external','compound','coastal'] as const)('legacy %s preserves exact executable input identity and storm clock',async mode=>{
 const flood={...config,mode},actual=scenarioInput(base,flood,null);
 const coastal=mode==='coastal'?boundary:undefined;
 const legacy={...base,coastal,depth:coastal?coastalInitialDepth(base,coastal):base.depth,inflows:mode==='external'||mode==='compound'?flood.inflows:[],outlets:flood.outlets};
 expect(await inputIdentity(actual)).toBe(await inputIdentity(legacy));
 const duration=mode==='coastal'?1200:60;
 const end=Math.max(duration+(mode==='coastal'?600:30),...((mode==='external'||mode==='compound')?[2400]:[]));
 expect(composeForcing(flood,rain).storm).toEqual({duration,recession:end-duration,depth:mode==='rain'||mode==='compound'?.01:0,intervals:mode==='rain'||mode==='compound'?rain.intervals:undefined});
});

test('combined sources retain independent rainfall timing and every enabled physical source',()=>{
 const flood: FloodConfiguration={...config,mode:'combined',components:{rainfall:true,external:true,coastal:true}};
 const forcing=composeForcing(flood,rain),input=scenarioInput(base,flood,null);
 validateScenarioExecution(input,forcing);
 expect(input.coastal).toEqual(boundary);expect(input.inflows).toEqual(config.inflows);
 expect(forcing.storm).toEqual({...composeForcing({...config,mode:'compound'},rain).storm});
 expect(rainfallAt(forcing.storm,10).rate).toBe(.0005);
 expect(rainfallAt(forcing.storm,40).rate).toBe(0);
 expect(forcing.storm.duration+forcing.storm.recession).toBe(2400);
 expect([...input.depth!]).toEqual([...coastalInitialDepth(base,boundary)]);
});

test('long coastal forcing extends recession without diluting or repeating uniform rain',()=>{
 const flood: FloodConfiguration={...config,mode:'combined',components:{rainfall:true,external:false,coastal:true}};
 const forcing=composeForcing(flood,{...rain,intervals:undefined});
 expect(forcing.storm.duration).toBe(60);expect(forcing.storm.recession).toBe(1740);
 expect(rainfallAt(forcing.storm,10).rate*60).toBe(.01);
 expect(rainfallAt(forcing.storm,61).rate).toBe(0);
});

test('disabled sources stay saved but cannot leak into execution or rainfall',()=>{
 const flood: FloodConfiguration={...config,mode:'combined',components:{rainfall:false,external:true,coastal:false}};
 const f=composeForcing(flood,rain),input=scenarioInput(base,flood,null);
 expect(f.storm.depth).toBe(0);expect(f.storm.intervals).toBeUndefined();expect(input.coastal).toBeUndefined();
 expect(flood.coastal).toBe(boundary);
});

test('incomplete, empty and overlapping compositions are rejected before a worker starts',()=>{
 const combined: FloodConfiguration={...config,mode:'combined',components:{rainfall:true,external:true,coastal:true}};
 for(const f of [
  {...combined,coastal:undefined},
  {...combined,inflows:[]},
  {...combined,components:{rainfall:false,external:false,coastal:false}},
  {...combined,inflows:[{...config.inflows[0],cell:0}]},
 ])expect(()=>validateScenarioExecution(scenarioInput(base,f,null),composeForcing(f,rain))).toThrow();
 expect(()=>forcingComponents({...combined,components:undefined})).toThrow();
 expect(()=>forcingComponents({...combined,mode:'unknown' as any})).toThrow();
});

test('toggling sources changes physical identity; rainfall edits change storm identity',async()=>{
 const both: FloodConfiguration={...config,mode:'combined',components:{rainfall:true,external:false,coastal:true}};
 expect(await inputIdentity(scenarioInput(base,both,null))).not.toBe(await inputIdentity(scenarioInput(base,{...both,components:{rainfall:true,external:false,coastal:false}},null)));
 expect(JSON.stringify(composeForcing(both,{...rain,intervals:undefined}).storm)).not.toBe(JSON.stringify(composeForcing(both,{...rain,depthMm:20,intervals:undefined}).storm));
});

test('execution rejects a compiler or caller dropping enabled sources',()=>{
 const flood: FloodConfiguration={...config,mode:'combined',components:{rainfall:true,external:true,coastal:true}};
 const input=scenarioInput(base,flood,null),forcing=composeForcing(flood,rain);
 expect(()=>validateScenarioExecution({...input,inflows:[]},forcing)).toThrow('does not match');
 expect(()=>validateScenarioExecution({...input,coastal:undefined},forcing)).toThrow('does not match');
});
