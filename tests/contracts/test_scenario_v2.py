import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from services.api.scenario_admission import assess_scenario
from services.api.scenario_contract import ScenarioSpecV2

CASES=json.loads(Path('packages/contracts/fixtures/scenario-v2-cases.json').read_text())


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_shared_scenario_cases(case):
    if not case['valid']:
        with pytest.raises(ValidationError):ScenarioSpecV2.model_validate(case['scenario'])
        return
    spec=ScenarioSpecV2.model_validate(case['scenario'])
    assessment=assess_scenario(spec)
    assert assessment['compatible']==case['compatible']
    assert assessment['data_validation']=='not_assessed'
    assert assessment['observed_accuracy']=='unvalidated'
    if spec.forcing.components.coastal:
        assert 'prescribed_coastal_level' in assessment['required_capabilities']


def test_assessment_endpoint_is_read_only_authenticated_and_rejects_invalid_contract():
    from services.api.main import app, identity
    client=TestClient(app)
    assert client.post('/api/v1/scenarios/assess',json=CASES[0]['scenario']).status_code==401
    app.dependency_overrides[identity]=lambda:'test-session'
    try:
        response=client.post('/api/v1/scenarios/assess',json=CASES[0]['scenario'])
        assert response.status_code==200
        assert response.json()==assess_scenario(ScenarioSpecV2.model_validate(CASES[0]['scenario']))
        invalid=next(c for c in CASES if not c['valid'])
        assert client.post('/api/v1/scenarios/assess',json=invalid['scenario']).status_code==422
    finally:
        app.dependency_overrides.pop(identity,None)
