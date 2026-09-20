import {expect,test} from 'vitest';
import {interventionEffects} from '../../packages/metrics/intervention-effects';
import type {PhysicalDesign} from '../../packages/domain/interventions';

const input={nx:3,ny:2,dx:2,dy:2,z:new Float32Array(6),solid:new Uint8Array([0,0,0,0,1,0]),planningWaterMask:new Uint8Array([0,0,0,0,0,1]),rainWeights:new Float32Array(6),roughness:new Float32Array(6),infiltration:new Float32Array(6),capacity:new Float32Array(6)};
const design:PhysicalDesign={id:'swale-a',kind:'bioswale',cells:[0,1],eligibility:'user_assumed',excavationM:.2,storageDepthM:.3,conductivityMS:.00001,percolationMS:0,roughness:.08,costMinor:100,parameterSource:'test'};

test('derives honest intervention storage and neighbourhood depth changes from replay frames',()=>{
 const baseline={depth:new Float32Array([.2,.1,.2,0,0,0]),maxDepth:new Float32Array([.3,.2,.2,0,0,0]),subsurfaceDepth:new Float32Array(6),ledger:{surface_m3:10,deep_percolation_m3:1,outflow_m3:0}};
 const planned={depth:new Float32Array([.1,.05,.1,.06,0,0]),maxDepth:new Float32Array([.2,.1,.1,.06,0,0]),subsurfaceDepth:new Float32Array([.2,.1,0,0,0,0]),ledger:{surface_m3:7,deep_percolation_m3:2.5,outflow_m3:.5}};
 const result=interventionEffects(input,baseline,planned,[design]);
 expect(result.byDesign[0]).toMatchObject({configuredStorageM3:4,status:'receiving_runoff'});
 expect(result.byDesign[0].surfaceM3).toBeCloseTo(.6);expect(result.byDesign[0].belowGroundM3).toBeCloseTo(1.2);expect(result.byDesign[0].waterAtFootprintM3).toBeCloseTo(1.8);expect(result.byDesign[0].baselineWaterAtFootprintM3).toBeCloseTo(1.2);expect(result.byDesign[0].fillFraction).toBeCloseTo(.45);
 expect(result).toMatchObject({surfaceWaterDifferenceM3:-3,deepPercolationDifferenceM3:1.5,externalDischargeDifferenceM3:.5,improvedAreaM2:4,worsenedAreaM2:4});expect(result.waterAtInterventionsM3).toBeCloseTo(1.8);expect(result.footprintWaterDifferenceM3).toBeCloseTo(.6);
});

test('rejects duplicate intervention cells instead of double-counting water',()=>{
 const frame={depth:new Float32Array(6),maxDepth:new Float32Array(6),ledger:{}};
 expect(()=>interventionEffects(input,frame,frame,[design,{...design,id:'other'}])).toThrow('Invalid intervention replay cells');
});
