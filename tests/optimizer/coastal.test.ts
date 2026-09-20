import {test,expect} from 'vitest';
import {coastalInitialDepth,coastalLevel,validateCoastal,type CoastalBoundary} from '../../packages/simulation/src/coastal';
const boundary:CoastalBoundary={edge:'west',cells:[0,4,8,12],levels:[{timeS:0,elevationM:1},{timeS:10,elevationM:2},{timeS:20,elevationM:1}],source:'test assumption',datum:'local metres'};
test('coastal levels interpolate and hold endpoints without changing the datum',()=>{
 expect([0,5,10,15,20,30].map(t=>coastalLevel(boundary,t))).toEqual([1,1.5,2,1.5,1,1]);
 expect(()=>validateCoastal({nx:4,ny:4,solid:new Uint8Array(16),coastal:{...boundary,datum:''}})).toThrow('datum');
 expect(()=>validateCoastal({nx:4,ny:4,solid:new Uint8Array(16),coastal:{...boundary,cells:[1]}})).toThrow('cell');
});
test('initial sea fills only connected terrain, keeping isolated low basins dry',()=>{
 const z=new Float32Array(16);for(let y=0;y<4;y++)z[y*4+1]=2;
 const input={nx:4,ny:4,z,solid:new Uint8Array(16)},depth=coastalInitialDepth(input,boundary);
 expect([...depth]).toEqual([1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0]);
 expect(z[1]).toBe(2);
});
