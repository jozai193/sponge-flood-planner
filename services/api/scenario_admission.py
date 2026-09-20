"""Read-only scenario capability assessment, never a solver dispatch."""
import json
from pathlib import Path

from services.api.scenario_contract import ScenarioSpecV2

REGISTRY=json.loads((Path(__file__).resolve().parents[2]/'packages/contracts/engine-capabilities.json').read_text(encoding='utf8'))


def assess_scenario(spec: ScenarioSpecV2):
    c=spec.forcing.components
    requested=set(spec.required_capabilities)
    if c.rainfall:requested.add('rainfall')
    if c.external:requested.add('external_inflow')
    if c.coastal:requested.add('prescribed_coastal_level')
    if sum((c.rainfall,c.external,c.coastal))>1:requested.add('combined_forcing')
    if spec.forcing.outlets:requested.add('parameterised_outlets')
    engine=REGISTRY['engines'].get(spec.engine)
    unsupported=sorted(requested-set(engine['capabilities'] if engine else []))
    reasons=[] if engine else [REGISTRY['unavailable'].get(spec.engine,'Unknown engine; no fallback was selected.')]
    reasons.extend('Unsupported capability: '+item for item in unsupported)
    return {'engine':spec.engine,'compatible':not reasons,'required_capabilities':sorted(requested),
            'unsupported_capabilities':unsupported,'reasons':reasons,
            'execution':engine['execution'] if engine else None,
            'data_validation':'not_assessed','observed_accuracy':'unvalidated',
            'limitations':['Capability compatibility does not verify terrain, datum alignment, solid-cell masks, source provenance or site accuracy.','No computation was started; executable arrays and identities require validation at dispatch.']}
