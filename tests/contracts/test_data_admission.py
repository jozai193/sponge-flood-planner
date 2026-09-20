import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from services.api.data_admission import assess_scenario_data
from services.api.scenario_contract import ScenarioSpecV2

CASES=json.loads(Path('packages/contracts/fixtures/data-admission-cases.json').read_text(encoding='utf8'))


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_data_suitability(case):
    spec=ScenarioSpecV2.model_validate(case['scenario'])
    result=assess_scenario_data(spec,case['manifest'])
    assert result['exploratory_allowed']==(not case['unsupported'])
    assert result['status']==('unsupported' if case['unsupported'] else 'needs_data')
    assert result['observed_accuracy']=='unvalidated'
    checks={c['id']:c for c in result['checks']}
    if case['expected_check']:
        key,status=case['expected_check'];assert checks[key]['status']==status
    assert ('bathymetry' in checks)==spec.forcing.components.coastal
    assert ('rainfall' in checks)==spec.forcing.components.rainfall
    assert ('external_inflow' in checks)==spec.forcing.components.external


def test_endpoint_uses_authorized_stored_manifest(monkeypatch,tmp_path):
    import services.api.main as api
    client=TestClient(api.app);body=CASES[0]['scenario']
    assert client.post('/api/v1/scenarios/assess-data',json=body).status_code==401
    (tmp_path/'manifest.json').write_text(json.dumps(CASES[0]['manifest']))
    calls=[]
    def access(bundle_id,session_id):
        calls.append((bundle_id,session_id))
        if bundle_id!=body['domain']['bundle_id']:raise HTTPException(404,'Bundle not found')
        return tmp_path
    monkeypatch.setattr(api,'bundle_access',access)
    api.app.dependency_overrides[api.identity]=lambda:'owner'
    try:
        r=client.post('/api/v1/scenarios/assess-data',json=body)
        assert r.status_code==200
        assert calls==[(body['domain']['bundle_id'],'owner')]
        assert r.json()['data']==assess_scenario_data(ScenarioSpecV2.model_validate(body),CASES[0]['manifest'])
        assert client.post('/api/v1/scenarios/assess-data',json={**body,'manifest':{'quality':{'validated':True}}}).status_code==422
        wrong={**body,'domain':{**body['domain'],'bundle_id':'b'*64}}
        assert client.post('/api/v1/scenarios/assess-data',json=wrong).status_code==404
    finally:api.app.dependency_overrides.pop(api.identity,None)
