import {test,expect} from 'vitest';
import {rainfallAt,validateRainfall,rainfallSensitivityEnsemble} from '../../packages/simulation/src/rainfall';
const storm={duration:10,recession:5,depth:.003,intervals:[{start_s:2,end_s:5,rate_m_s:.001}]};
test('measured rainfall retains dry gaps and clips at interval boundaries',()=>{
 validateRainfall(storm);
 expect(rainfallAt(storm,0)).toEqual({rate:0,knot:2});
 expect(rainfallAt(storm,2)).toEqual({rate:.001,knot:5});
 expect(rainfallAt(storm,5)).toEqual({rate:0,knot:15});
});
test('sensitivity ensemble preserves timing and exact interval integrals',()=>{
 const source={duration:10,recession:5,depth:.0015,intervals:[{start_s:2,end_s:5,rate_m_s:.0005}]},members=rainfallSensitivityEnsemble(source);
 expect(members.map(m=>m.depth)).toEqual([expect.closeTo(.0012,12),expect.closeTo(.0015,12),expect.closeTo(.0018,12)]);
 for(const member of members){validateRainfall(member);expect(member.duration).toBe(source.duration);expect(member.recession).toBe(source.recession);}
 expect(()=>rainfallSensitivityEnsemble(source,[])).toThrow('factors');
});
test('inconsistent event depth and overlapping intervals fail',()=>{
 expect(()=>validateRainfall({duration:10,recession:0,depth:0,intervals:[{start_s:0,end_s:1,rate_m_s:.001}]})).toThrow();
 expect(()=>validateRainfall({duration:10,recession:0,depth:.004,intervals:[{start_s:0,end_s:3,rate_m_s:.001},{start_s:2,end_s:3,rate_m_s:.001}]})).toThrow();
});
