import pytest
from pydantic import ValidationError

from services.api.contracts import Design, Grid, Intervention, PlanningRequest, Storm, content_hash


def test_rain_integral_and_overlap():
    storm = Storm(name="controlled", duration_s=3600, recession_s=0, depth_m=.1,
                  intervals=[{"start_s": 0, "end_s": 3600, "rate_m_s": .1/3600}])
    assert storm.depth_m == .1
    with pytest.raises(ValidationError):
        Storm(**{**storm.model_dump(), "depth_m": .2})


def test_nonfinite_and_grid_bounds():
    with pytest.raises(ValidationError):
        Grid(nx=32, ny=32, dx_m=float("nan"), dy_m=1)
    with pytest.raises(ValidationError):
        Grid(nx=3000, ny=32, dx_m=1, dy_m=1)


def test_budget_overlap_and_eligibility():
    i = Intervention(id="a", kind="rain_garden", cells=[1, 2], cost_minor=100, eligibility="confirmed")
    with pytest.raises(ValidationError):
        Design(interventions=[i], budget_minor=99)
    with pytest.raises(ValidationError):
        Design(interventions=[i, i.model_copy(update={"id": "b"})])
    with pytest.raises(ValidationError):
        Design(interventions=[i.model_copy(update={"eligibility": "unverified"})])


def test_identity_order_and_physical_changes():
    assert content_hash({"x": 1, "y": 2}) == content_hash({"y": 2, "x": 1})
    assert content_hash({"x": 1}) != content_hash({"x": 2})


def test_provider_neutral_proposal_contract_validates_catalogue_constraints():
    request=PlanningRequest(bundle_id="b",candidate_ids=["a","b"],budget_minor=100,locked_ids=["a"],excluded_ids=["b"],source_references=["urn:source:catalog-v1"])
    assert request.locked_ids==["a"]
    with pytest.raises(ValidationError):PlanningRequest(bundle_id="b",candidate_ids=["a"],budget_minor=1,locked_ids=["missing"])
    with pytest.raises(ValidationError):PlanningRequest(bundle_id="b",candidate_ids=["a"],budget_minor=1,locked_ids=["a"],excluded_ids=["a"])
