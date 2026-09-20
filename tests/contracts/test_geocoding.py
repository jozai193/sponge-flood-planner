import json

import httpx
import pytest

from services.geodata.geocoding import search_places


def search(fetcher, allow=lambda _: True):
    return search_places(
        "Some apartments, Example city",
        nominatim_url="nominatim",
        photon_url="photon",
        allow_request=allow,
        fetcher=fetcher,
    )


def photon(name="Some apartments", lat=12, lon=77):
    return {
        "features": [
            {
                "properties": {"name": name, "city": "Example city", "country": "India"},
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            }
        ]
    }


def test_fuzzy_candidates_survive_unrelated_exact_matches():
    def fetcher(url, params, **kwargs):
        assert params["q"] == "Some apartments, Example city"
        assert kwargs["max_age_s"] == 86400
        data = (
            photon() if url == "photon" else [{"display_name": "Unrelated parking", "lat": 45, "lon": -122}]
        )
        return json.dumps(data).encode(), {"source_url": url}

    result = search(fetcher)
    assert [r["latitude"] for r in result["locations"]] == [12, 45]
    assert len(result["sources"]) == 2


def test_provider_outage_keeps_other_results():
    def fetcher(url, *args, **kwargs):
        if url == "nominatim":
            raise httpx.ReadTimeout("offline")
        return json.dumps(photon()).encode(), {}

    result = search(fetcher)
    assert len(result["locations"]) == 1
    assert "Nominatim" in result["warnings"][0]


@pytest.mark.parametrize(
    "data", [{}, None, {"features": None}, {"features": [None, {}, {"properties": None}]}]
)
def test_malformed_provider_responses_do_not_crash(data):
    result = search(lambda *a, **k: (json.dumps(data).encode(), {}))
    assert result["locations"] == []


def test_duplicates_and_invalid_coordinates():
    def fetcher(url, *a, **k):
        return json.dumps(
            photon()
            if url == "photon"
            else [
                {"display_name": "Same place", "lat": 12, "lon": 77},
                {"display_name": "Bad", "lat": 100, "lon": 20},
            ]
        ).encode(), {}

    assert len(search(fetcher)["locations"]) == 1


def test_rate_limited_provider_is_not_called():
    def fetcher(*a, **k):
        raise AssertionError("must not call provider")

    result = search(fetcher, allow=lambda _: False)
    assert not result["locations"]
    assert len(result["warnings"]) == 2


def test_region_is_forwarded_and_coordinate_coverage_is_separate(monkeypatch):
    from services.api import main
    from services.api.contracts import PrepareRequest

    class Connection:
        def set(self, *args, **kwargs):
            return True

    monkeypatch.setattr(main.Redis, "from_url", lambda *_args, **_kwargs: Connection())

    def fake(query, **kwargs):
        assert query == "Some apartments, Example city"
        return {"locations": []}

    monkeypatch.setattr(main, "search_places", fake)
    main.geocode({"query": "Some apartments", "region": "Example city"}, session_id="test")
    with pytest.raises(ValueError):
        PrepareRequest(latitude=89, longitude=0)
