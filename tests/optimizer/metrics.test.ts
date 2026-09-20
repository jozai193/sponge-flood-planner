import {test,expect} from 'vitest';
import {eventLoss,fraction} from '../../packages/metrics';
const curve={id:'synthetic-test',source:'controlled fixture, not real building economics',points:[[0,0],[1,.5],[2,1]] as [number,number][]};
test('loss uses exterior elevation relative to first floor, once per asset',()=>{
 const assets=[{id:'a',exteriorCells:[0,1],firstFloorElevationM:10,structureValueMinor:10000,curve}];
 expect(eventLoss(assets,new Float32Array([10,11])).totalMinor).toBe(5000);
 expect(eventLoss(assets,new Float32Array([10,11])).totalMinor).toBe(5000);
 expect(eventLoss([{...assets[0],structureValueMinor:null}],new Float32Array([10,11])).totalMinor).toBeNull();
 expect(fraction(-1,curve)).toBe(0);
});
