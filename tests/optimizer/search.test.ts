import {test,expect} from 'vitest';
import {search,feasible} from '../../packages/optimizer';
const catalog=[{id:'a',costMinor:4,conflicts:[]},{id:'b',costMinor:4,conflicts:[]},{id:'c',costMinor:8,conflicts:['b']}];
const options={budgetMinor:8,locked:[],excluded:[],maxEvaluations:100};
test('finds complementary pair and reports exhaustive only for enumerated set',async()=>{
 const r=await search(catalog,async ids=>ids.includes('a')&&ids.includes('b')?1:ids.includes('c')?5:10,options);
 expect(r.selected).toEqual(['a','b']);expect(r.status).toBe('exhaustive');expect(r.costMinor).toBe(8);
 expect(r.elapsedMs).toBeGreaterThanOrEqual(0);expect(r.terminationReason).toContain('Every feasible subset');
});
test('zero budget and exclusions preserve feasibility',async()=>{
 expect((await search(catalog,async ids=>10-ids.length,{...options,budgetMinor:0})).selected).toEqual([]);
 expect(feasible(['b','c'],catalog,{...options,budgetMinor:20})).toBe(false);
 await expect(search(catalog,async()=>0,{...options,locked:['a'],excluded:['a']})).rejects.toThrow('infeasible');
});
test('invalid scores and evaluation budgets cannot claim optimum',async()=>{
 await expect(search(catalog,async()=>NaN,options)).rejects.toThrow('non-finite');
 const r=await search(catalog,async()=>10,{...options,maxEvaluations:1});expect(r.status).toBe('budget_exhausted');expect(r.evaluations).toBe(1);
});
test('honours required and disabled sites throughout nonlinear search',async()=>{
 const r=await search(catalog,async ids=>ids.includes('c')?0:ids.length,{...options,budgetMinor:12,locked:['a'],excluded:['c']});
 expect(r.selected).toContain('a');expect(r.selected).not.toContain('c');
 expect(r.evaluated.every(item=>item.selected.includes('a')&&!item.selected.includes('c'))).toBe(true);
});
