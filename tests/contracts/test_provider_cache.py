import hashlib
import json

import httpx
import pytest

from services.geodata import providers


@pytest.mark.parametrize('damage',['none','bytes','metadata','mismatch'])
def test_cache_integrity_and_recovery(monkeypatch,tmp_path,damage):
    monkeypatch.setattr(providers,'CACHE',tmp_path)
    requests=[]
    def respond(request):
        requests.append(request)
        return httpx.Response(200,content=b'correct data')
    original=httpx.Client
    monkeypatch.setattr(providers.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    url='https://example.test/data'
    first,source=providers.fetch(url)
    key=hashlib.sha256((url+'{}').encode()).hexdigest()
    if damage=='bytes':(tmp_path/key).write_bytes(b'partial')
    if damage=='metadata':(tmp_path/(key+'.json')).write_text('{')
    if damage=='mismatch':
        altered={**source,'sha256':'wrong'}
        (tmp_path/(key+'.json')).write_text(json.dumps(altered))
    second,verified=providers.fetch(url)
    assert second==first==b'correct data'
    assert verified['sha256']==hashlib.sha256(second).hexdigest()
    assert len(requests)==(1 if damage=='none' else 2)
    assert len(list(tmp_path.iterdir()))==2


def test_cache_does_not_bypass_smaller_download_limit(monkeypatch,tmp_path):
    monkeypatch.setattr(providers,'CACHE',tmp_path)
    original=httpx.Client
    monkeypatch.setattr(providers.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b'123456')),**kw))
    providers.fetch('https://example.test/data')
    with pytest.raises(ValueError,match='bounded download'):
        providers.fetch('https://example.test/data',max_bytes=3)


@pytest.mark.parametrize('retrieved_at',['2000-01-01T00:00:00+00:00',None,'invalid'])
def test_expiring_search_cache_reacquires_old_or_undated_data(monkeypatch,tmp_path,retrieved_at):
    monkeypatch.setattr(providers,'CACHE',tmp_path)
    requests=[]
    def respond(request):
        requests.append(request)
        return httpx.Response(200,content=b'[]')
    original=httpx.Client
    monkeypatch.setattr(providers.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    url='https://example.test/search'
    _,source=providers.fetch(url)
    meta=tmp_path/(hashlib.sha256((url+'{}').encode()).hexdigest()+'.json')
    meta.write_text(json.dumps({**source,'retrieved_at':retrieved_at}))
    # Existing scientific source caches retain their original behavior.
    providers.fetch(url)
    assert len(requests)==1
    providers.fetch(url,max_age_s=86400)
    assert len(requests)==2
    providers.fetch(url,max_age_s=86400)
    assert len(requests)==2
