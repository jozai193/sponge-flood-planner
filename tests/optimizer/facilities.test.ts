import {test,expect} from 'vitest';
import {exchangeFacilities,type FacilityLink} from '../../packages/simulation/src/facilities';
import {compileDesign,type PhysicalDesign} from '../../packages/domain/interventions';
import {inputIdentity} from '../../packages/simulation/src/identity';
const base=()=>({nx:4,ny:4,dx:2,dy:3,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16),capacity:new Float32Array(16),infiltration:new Float32Array(16)});
const design:PhysicalDesign={id:'a',kind:'rain_garden',cells:[0,1],eligibility:'user_assumed',excavationM:.2,storageDepthM:.1,conductivityMS:.001,percolationMS:0,roughness:.1,costMinor:0,parameterSource:'analytic fixture'};
test('run identity changes with facility destination, control rate and execution timestep',async()=>{
 const input=compileDesign(base(),[{...design,underdrain:{targetCell:15,crestDepthM:0,ratePerS:.1,maxFlowM3S:.01}}],0);
 const original=await inputIdentity(input);
 expect(await inputIdentity({...input,maxStepS:10})).not.toBe(original);
 for(const change of [{targetCell:null},{ratePerS:.2}])expect(await inputIdentity({...input,facilityLinks:input.facilityLinks!.map(link=>({...link,...change}))})).not.toBe(original);
 expect(await inputIdentity(input)).toBe(original);
});
test('underdrain returns conserve storage with multiple donors and an external sink',()=>{
 const links:FacilityLink[]=[0,1,2].map(cell=>({cell,targetCell:cell===2?null:3,reservoir:'subsurface',crestDepthM:.02,ratePerS:.2,maxFlowM3S:100,source:'analytic'}));
 const soil=new Float64Array(16).fill(.1),h=new Float64Array(16),z=new Float32Array(16);
 const r=exchangeFacilities(h,soil,z,6,links,2),released=.08*(1-Math.exp(-.4));
 expect(r.storage[0]).toBeCloseTo(.1-released,12);expect(r.depth[3]).toBeCloseTo(2*released,12);expect(r.exportedM3).toBeCloseTo(6*released,12);
 expect((r.depth.reduce((a,b)=>a+b,0)+r.storage.reduce((a,b)=>a+b,0))*6+r.exportedM3).toBeCloseTo(9.6,12);
 expect(exchangeFacilities(h,soil,z,6,[...links].reverse(),2)).toEqual(r);
});
test('surface controls respect crest, receiver head, capacity and donor water',()=>{
 const h=new Float64Array(16);h[0]=.5;h[1]=.6;
 const link:FacilityLink={cell:0,targetCell:1,reservoir:'surface',crestDepthM:.1,ratePerS:100,maxFlowM3S:1,source:'test'};
 expect(exchangeFacilities(h,h.map(()=>0),new Float32Array(16),6,[link],1).depth[0]).toBe(.5);
 h[1]=0;link.maxFlowM3S=.06;
 expect(exchangeFacilities(h,h.map(()=>0),new Float32Array(16),6,[link],1).depth[0]).toBeCloseTo(.49,12);
 link.targetCell=null;link.maxFlowM3S=100;
 expect(exchangeFacilities(h,h.map(()=>0),new Float32Array(16),6,[link],1).depth[0]).toBeCloseTo(.1,12);
});
test('four designs compile distinct geometry, permeability and explicit discharge without mutating baseline',()=>{
 const b=base(),control={targetCell:15,crestDepthM:0,ratePerS:.01,maxFlowM3S:.002};
 const garden=compileDesign(b,[{...design,underdrain:control}],0);
 expect(garden.facilityLinks).toHaveLength(2);expect(garden.facilityLinks![0].maxFlowM3S).toBe(.001);expect(b.capacity[0]).toBe(0);
 const swale=compileDesign(b,[{...design,kind:'bioswale',swaleSlope:.02,swaleAxis:'x'}],0);expect(swale.z[0]-swale.z[1]).toBeCloseTo(.04,6);
 const pavement=compileDesign(b,[{...design,kind:'permeable_pavement',excavationM:0,cloggingFraction:.75}],0);expect(pavement.z[0]).toBe(0);expect(pavement.infiltration[0]).toBeCloseTo(.00025,8);
 const basin=compileDesign(b,[{...design,kind:'detention_basin',storageDepthM:0,surfaceControl:control}],0);expect(basin.capacity[0]).toBe(0);expect(basin.facilityLinks![0].reservoir).toBe('surface');
 expect(()=>compileDesign(b,[{...design,underdrain:{...control,targetCell:0}}],0)).toThrow('outside');
 expect(()=>compileDesign(b,[{...design,underdrain:{...control,maxFlowM3S:-1}}],0)).toThrow('control');
});
