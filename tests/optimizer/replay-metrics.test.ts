import {expect,test} from 'vitest';
import {localWorseningArea,replayMetrics} from '../../packages/metrics/replay';

const input={nx:2,ny:2,dx:2,dy:3,z:new Float32Array(4),solid:new Uint8Array([0,0,1,0]),rainWeights:new Float32Array(4),roughness:new Float32Array(4),infiltration:new Float32Array(4),capacity:new Float32Array(4)};
test('derives exposure from stored running maxima and a configurable threshold',()=>{
 const frame={maxDepth:new Float32Array([.05,.2,.8,.3]),ledger:{surface_m3:1,subsurface_m3:2,deep_percolation_m3:3,outflow_m3:4}};
 expect(replayMetrics(input,frame,[{id:'a',exterior_cells:[0,1]},{id:'b',exterior_cells:[3]}],.25)).toEqual({
  affectedBuildings:1,peakDepthM:.30000001192092896,areaAboveThresholdM2:6,surfaceM3:1,subsurfaceM3:2,deepPercolationM3:3,outflowM3:4});
});
test('reports local adverse changes outside solids and permanent water',()=>{
 const withWater={...input,planningWaterMask:new Uint8Array([0,1,0,0])};
 expect(localWorseningArea(withWater,new Float32Array(4),new Float32Array([.05,.2,.5,.049]))).toBe(6);
});
