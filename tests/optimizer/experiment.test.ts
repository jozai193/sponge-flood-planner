import {expect,test} from 'vitest';
import {floodScore} from '../../packages/simulation/src/experiment';
import type {GPUInput} from '../../packages/simulation/src/gpu';
test('fixed receptor mask excludes facilities and buildings without rewarding hidden storage depth',()=>{
 const input={dx:2,dy:3,solid:new Uint8Array([0,0,1,0])} as GPUInput;
 expect(floodScore({maxDepth:new Float32Array([.2,2,3,.05])},input,new Set([1]))).toBeCloseTo(.6);
 expect(()=>floodScore({maxDepth:new Float32Array([NaN])},input,new Set())).toThrow();
});
