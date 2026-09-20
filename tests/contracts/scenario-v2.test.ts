import {test,expect} from 'vitest';
import cases from '../../packages/contracts/fixtures/scenario-v2-cases.json';
import {parseScenarioSpec,assessScenario,sameScenarioValue} from '../../packages/domain/scenario-wire';

test.each(cases)('$name: shared contract and engine assessment',c=>{
 if(!c.valid){expect(()=>parseScenarioSpec(c.scenario)).toThrow();return;}
 const spec=parseScenarioSpec(c.scenario),assessment=assessScenario(spec);
 expect(assessment.compatible).toBe(c.compatible);
 expect(assessment.data_validation).toBe('not_assessed');
 expect(assessment.observed_accuracy).toBe('unvalidated');
 if(spec.forcing.components.coastal)expect(assessment.required_capabilities).toContain('prescribed_coastal_level');
});

test('cross-language key order and optional nulls do not change source equality',()=>{
 expect(sameScenarioValue({cell:1,source:'test'},{source:'test',cell:1,tailwaterElevationM:null})).toBe(true);
 expect(sameScenarioValue({cell:1,source:'test'},{cell:2,source:'test'})).toBe(false);
});

test('wire round trip preserves source precision and rejects non-finite numbers',()=>{
 const spec=parseScenarioSpec(cases[0].scenario);
 expect(parseScenarioSpec(JSON.parse(JSON.stringify(spec)))).toEqual(spec);
 expect(()=>parseScenarioSpec({...spec,domain:{...spec.domain,dx_m:NaN}})).toThrow();
 expect(()=>parseScenarioSpec({...spec,domain:{...spec.domain,dy_m:Infinity}})).toThrow();
});
