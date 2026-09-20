import {test,expect} from 'vitest';
import cases from '../../packages/contracts/fixtures/data-admission-cases.json';
import {parseScenarioSpec} from '../../packages/domain/scenario-wire';
import {assessScenarioData} from '../../packages/domain/data-admission';

test.each(cases)('$name: data suitability',c=>{
 const spec=parseScenarioSpec(c.scenario),r=assessScenarioData(spec,c.manifest);
 expect(r.exploratory_allowed).toBe(!c.unsupported);
 expect(r.status).toBe(c.unsupported?'unsupported':'needs_data');
 expect(r.observed_accuracy).toBe('unvalidated');
 if(c.expected_check)expect(r.checks.find(v=>v.id===c.expected_check![0])?.status).toBe(c.expected_check[1]);
 expect(r.checks.some(v=>v.id==='bathymetry')).toBe(spec.forcing.components.coastal);
 expect(r.checks.some(v=>v.id==='rainfall')).toBe(spec.forcing.components.rainfall);
 expect(r.checks.some(v=>v.id==='external_inflow')).toBe(spec.forcing.components.external);
});

test('missing manifest cannot admit a scenario',()=>{
 expect(assessScenarioData(parseScenarioSpec(cases[0].scenario),null).exploratory_allowed).toBe(false);
});
