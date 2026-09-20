import {test,expect} from 'vitest';
import {ratingFlow,exchangeFacilities,type FacilityLink,type ControlRating} from '../../packages/simulation/src/facilities';
import {waterGeometry} from '../../apps/web/src/water';
import {compileDesign} from '../../packages/domain/interventions';
test('facility ratings divide physical dimensions once and select the tested timestep',()=>{
 const input={nx:4,ny:4,dx:1,dy:1,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16),roughness:new Float32Array(16),infiltration:new Float32Array(16),capacity:new Float32Array(16)};
 const control={targetCell:null,crestDepthM:.1,ratePerS:0,maxFlowM3S:.1,rating:{kind:'orifice' as const,areaM2:.02,coefficient:.6}};
 const d={id:'a',kind:'detention_basin' as const,cells:[0,1],eligibility:'user_assumed' as const,excavationM:.2,storageDepthM:0,conductivityMS:0,percolationMS:0,roughness:.03,costMinor:0,parameterSource:'test',surfaceControl:control};
 const result=compileDesign(input,[d],0);expect(result.maxStepS).toBe(.2);expect(result.facilityLinks![0].rating).toEqual({...control.rating,areaM2:.01});expect(control.rating.areaM2).toBe(.02);
 expect(()=>compileDesign(input,[{...d,surfaceControl:{...control,rating:{...control.rating,coefficient:-1}}}],0)).toThrow('coefficient');
});
test('SI orifice and sharp-crested ratings obey head, dimensions and submergence',()=>{
 expect(ratingFlow({kind:'orifice',areaM2:.1,coefficient:.6},2)).toBeCloseTo(.6*.1*Math.sqrt(2*9.80665*2),12);
 const weir:ControlRating={kind:'weir',widthM:2,coefficient:1.7};
 expect(ratingFlow(weir,1)).toBeCloseTo(3.4,12);
 expect(ratingFlow(weir,1,.5)).toBeCloseTo(3.4*(1-.5**1.5)**.385,12);
 expect(ratingFlow(weir,1,1)).toBe(0);expect(ratingFlow(weir,0)).toBe(0);
});
test('reference outlet recession converges to independent analytic solutions',()=>{
 for(const rating of [{kind:'orifice',areaM2:.5,coefficient:.6},{kind:'weir',widthM:2,coefficient:1.7}] as ControlRating[]){
  const k=rating.kind==='orifice'?.6*.5*Math.sqrt(2*9.80665)/100:1.7*2/100;
  const exact=rating.kind==='orifice'?(Math.sqrt(.5)-k*4/2)**2:(1/Math.sqrt(.5)+k*4/2)**-2;
  const errors=[.4,.2,.1].map(dt=>{
   let h=new Float64Array([.5]);const soil=new Float64Array(1),z=new Float32Array(1);
   const link:FacilityLink={cell:0,targetCell:null,reservoir:'surface',crestDepthM:0,ratePerS:0,maxFlowM3S:100,source:'analytic',rating};
   for(let i=0;i<Math.round(4/dt);i++)h=exchangeFacilities(h,soil,z,100,[link],dt).depth;
   return Math.abs(h[0]-exact);
  });
  expect(errors[1]).toBeLessThan(errors[0]*.6);expect(errors[2]).toBeLessThan(errors[1]*.6);expect(errors[2]).toBeLessThan(.0003);
 }
});
test('water graphics preserve data, skip dry/building cells, share edges and follow actual velocity',()=>{
 const input={nx:4,ny:4,dx:1,dy:1,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16),roughness:new Float32Array(16),infiltration:new Float32Array(16),capacity:new Float32Array(16)};
 const depth=new Float32Array(16);depth[0]=depth[1]=.1;depth[2]=1;input.solid[2]=1;
 const frame={depth,maxDepth:depth.slice(),velocityX:new Float32Array(16).fill(.5),velocityY:new Float32Array(16)};
 const before=depth.slice(),water=waterGeometry(input,frame);
 expect(water.walls.attributes.positions.value).toHaveLength(6*6*3);
 const exaggerated=waterGeometry(input,frame,5);expect(exaggerated.cells[0].polygon[0][2]).toBeCloseTo(.506,6);expect(exaggerated.cells[0].depth).toBe(depth[0]);
 expect(water.cells).toHaveLength(2);expect(water.cells[0].polygon[1]).toEqual(water.cells[1].polygon[0]);
 expect(water.cells[0].polygon[0][2]).toBeCloseTo(.106,6);expect(water.flow[0].target[0]).toBeGreaterThan(water.flow[0].source[0]);expect(depth).toEqual(before);
 expect(waterGeometry(input,{...frame,velocityX:new Float32Array(16)}).flow).toHaveLength(0);
});
