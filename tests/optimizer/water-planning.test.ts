import {test,expect} from 'vitest';
import {waterPlanningMask,dryCandidates} from '../../apps/web/src/water-planning';
import {compileDesign,type PhysicalDesign} from '../../packages/domain/interventions';
import {packInput,unpackInput} from '../../packages/metrics/report';
import {inputIdentity} from '../../packages/simulation/src/identity';
import type {GPUInput} from '../../packages/simulation/src/gpu';
const base=():GPUInput=>({nx:4,ny:4,dx:10,dy:10,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16).fill(.03),capacity:new Float32Array(16),infiltration:new Float32Array(16)});
const design:PhysicalDesign={id:'garden',kind:'rain_garden',cells:[3],eligibility:'user_assumed',excavationM:.2,storageDepthM:.1,conductivityMS:0,percolationMS:0,roughness:.03,costMinor:0,parameterSource:'test'};
test('water overlap excludes whole footprints, preserving adjacent dry cells and north-up rows',()=>{
 const input=base(),mask=waterPlanningMask(input,{roads:[],green:[],trees:[],assumptions:[],water:[{id:'water',name:'water',polygon:[[0,-20],[20,-20],[20,0],[0,0],[0,-20]]}]});
 expect([...mask]).toEqual([0,0,1,1,0,0,1,1,0,0,0,0,0,0,0,0]);
 expect(dryCandidates([{cells:[0,1]},{cells:[1,2]},{cells:[15]}],mask)).toEqual([{cells:[0,1]},{cells:[15]}]);
 expect(input.z.every(x=>x===0)).toBe(true);
});
test('compiler rejects water even with user-assumed eligibility; report and identity retain mask',async()=>{
 const input=base();input.planningWaterMask=new Uint8Array(16);input.planningWaterMask[3]=1;
 expect(()=>compileDesign(input,[design],0)).toThrow('permanent water');
 expect(()=>compileDesign(input,[{...design,cells:[2]}],0)).not.toThrow();
 const restored=unpackInput(JSON.parse(JSON.stringify(packInput(input))));
 expect(restored.planningWaterMask).toEqual(input.planningWaterMask);
 expect(await inputIdentity(restored)).toBe(await inputIdentity(input));
 expect(await inputIdentity({...input,planningWaterMask:new Uint8Array(16)})).not.toBe(await inputIdentity(input));
});
test('prohibited and protected candidate areas never reach the editor',()=>{
 const mask=new Uint8Array(4),sites=[{id:'ok',cells:[0]},{id:'no',cells:[1],eligibility:'prohibited'},{id:'protected',cells:[2],protected_reasons:['wetland']}];
 expect(dryCandidates(sites,mask)).toEqual([sites[0]]);
});
