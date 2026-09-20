import {describe,it,expect} from 'vitest';
import {correctDepthRoundoff,validateRoundoffBudget} from '../../packages/simulation/src/positivity-roundoff';

describe('experimental depth roundoff accounting',()=>{
  it('records the exact added volume and removes momentum only at corrected cells',()=>{
    const state=new Float32Array([-5e-12,1e-20,-1e-20,0,.1,2,3,.02]);
    const negative=state[0];const result=correctDepthRoundoff(state,61.03515625);
    expect(result).toEqual({volumeM3:-negative*61.03515625,cells:1,minDepthM:negative});
    expect(Array.from(state.slice(0,4))).toEqual([0,0,0,0]);
    expect(Array.from(state.slice(4))).toEqual(Array.from(new Float32Array([.1,2,3,.02])));
  });
  it('rejects material negatives or invalid subsurface state before any mutation',()=>{
    for(const bad of [-2e-10,Number.NaN,Number.NEGATIVE_INFINITY]){
      const state=new Float32Array([-5e-12,0,0,0,bad,0,0,0]),before=state.slice();
      expect(()=>correctDepthRoundoff(state,1)).toThrow('NUMERICAL_INVALID');expect(state).toEqual(before);
    }
    expect(()=>correctDepthRoundoff(new Float32Array([0,0,0,-5e-12]),1)).toThrow('material negative');
  });
  it('caps cumulative correction independently of the ordinary mass residual gate',()=>{
    expect(()=>validateRoundoffBudget(1e-10,1)).not.toThrow();
    for(const amount of [-1,NaN,Infinity,1.01e-8])expect(()=>validateRoundoffBudget(amount,1)).toThrow();
  });
});
