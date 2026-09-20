import {test,expect} from 'vitest';
import {INTERVENTION_CATALOG,INTERVENTION_SOURCES,catalogSourceText} from '../../packages/domain/intervention-catalog';

test('catalogue preserves all four distinct GI types and resolvable official sources',()=>{
 expect(Object.keys(INTERVENTION_CATALOG).sort()).toEqual(['bioswale','detention_basin','permeable_pavement','rain_garden']);
 for(const entry of Object.values(INTERVENTION_CATALOG)){
  expect(entry.sourceIds.length).toBeGreaterThan(0);
  for(const id of entry.sourceIds)expect(INTERVENTION_SOURCES[id as keyof typeof INTERVENTION_SOURCES].url).toMatch(/^https:\/\//);
  expect(catalogSourceText(entry.kind)).toContain(entry.note);
 }
 expect(INTERVENTION_CATALOG.permeable_pavement.defaults.excavationM).toBe(0);
 expect(INTERVENTION_CATALOG.detention_basin.defaults.storageDepthM).toBe(0);
});
