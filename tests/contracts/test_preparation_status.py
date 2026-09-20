from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from services.api import main
from services.api.contracts import PrepareRequest


@pytest.mark.parametrize("available", [False, True])
def test_queued_status_reports_worker_availability(monkeypatch, available):
    monkeypatch.setattr(main, "resource", lambda *args: SimpleNamespace(id="job", status="queued", payload={}))
    monkeypatch.setattr(main.Redis, "from_url", lambda *args, **kwargs: object())
    monkeypatch.setattr(main, "Queue", lambda *args, **kwargs: object())
    monkeypatch.setattr(main.Worker, "all", lambda **kwargs: [object()] if available else [])
    assert main.get_neighbourhood("job", "session")["worker_available"] is available

@pytest.mark.parametrize("same", [False, True])
def test_active_request_is_reused_only_for_same_location(monkeypatch, same):
    body=PrepareRequest(longitude=81.8,latitude=25.4,label="Prayagraj")
    request=body.model_dump()
    row=SimpleNamespace(id="existing",status="queued",payload={"request":request if same else {**request,"longitude":82}})
    db=MagicMock();db.scalars.return_value=[row]
    session=MagicMock();session.begin.return_value.__enter__.return_value=db
    monkeypatch.setattr(main,"Session",session)
    monkeypatch.setattr(main,"ensure_enqueued",lambda resource_id:resource_id=="existing")
    if same:
        assert main.new_neighbourhood(body,"session",None)=={"id":"existing","status":"queued"}
    else:
        with pytest.raises(HTTPException) as caught:main.new_neighbourhood(body,"session",None)
        assert caught.value.status_code==429
    db.add.assert_not_called()


def test_enqueue_failure_leaves_durable_preparation_queued_for_reconciliation(monkeypatch):
    body=PrepareRequest(longitude=81.8,latitude=25.4,label="Prayagraj")
    db=MagicMock();db.scalars.return_value=[]
    session=MagicMock();session.begin.return_value.__enter__.return_value=db
    monkeypatch.setattr(main,"Session",session)
    monkeypatch.setattr(main,"ensure_enqueued",lambda *_:(_ for _ in ()).throw(ConnectionError("redis unavailable")))

    with pytest.raises(HTTPException) as caught:
        main.new_neighbourhood(body,"session",None)

    assert caught.value.status_code==503
    db.add.assert_called_once()
