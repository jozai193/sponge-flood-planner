import {expect,test} from 'vitest';
import {inspectPick} from '../../apps/web/src/map-inspection';

test('resolves water, building and candidate picks to canonical cells',()=>{
 expect(inspectPick({i:5,depth:.123},16)).toEqual({kind:'cell',id:'5',cells:[5],message:'Simulation cell 5 · water depth 12.3 cm'});
 expect(inspectPick({id:'building-a',exterior_cells:[1,2]},16)?.cells).toEqual([1,2]);
 expect(inspectPick({id:'site-a',cells:[4,5,8,9]},16)?.message).toBe('Candidate site-a · 4 simulation cells');
 expect(inspectPick({id:'site-b',cells:[-1]},16)).toBeNull();
});
