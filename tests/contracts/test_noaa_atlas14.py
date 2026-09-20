import math

import pytest

from services.geodata import noaa_atlas14


def response():
    rows=[[str(10+row+column) for column in range(9)] for row in range(19)]
    lower=[[str(float(value)-1) for value in row] for row in rows]
    upper=[[str(float(value)+1) for value in row] for row in rows]
    return "\n".join([
        f"quantiles = {rows!r};", f"lower = {lower!r};", f"upper = {upper!r};",
        "lat = '39.9650';", "lon = '-75.1640';", "region = 'Ohio River Basin';",
        "volume = '2';", "version = '3';", "authors = 'NOAA authors';",
        "unit = 'metric';", "ser = 'ams';", "datatype = 'depth';",
    ]).encode()


def test_parses_bounded_assignment_format_without_execution():
    data=noaa_atlas14.parse_pfds(response().decode())
    assert data["quantiles"][4][6] == 20
    with pytest.raises(ValueError,match="missing quantiles"):
        noaa_atlas14.parse_pfds("__import__('os').system('bad')")


def test_builds_integral_preserving_sourced_design_storm(monkeypatch):
    monkeypatch.setattr(noaa_atlas14,"fetch",lambda *args,**kwargs:(response(),{
        "source_url":"https://hdsc.nws.noaa.gov/example","retrieved_at":"2026-09-19T00:00:00+00:00","sha256":"a"*64}))
    storm=noaa_atlas14.design_storm(latitude=39.965,longitude=-75.164,label="Spring Garden",
        duration_minutes=60,return_period_years=100,distribution="centered",antecedent_saturation=.75)
    assert storm["depth_m"] == .02
    assert storm["return_period_years"] == 100
    assert storm["antecedent_saturation"] == .75
    assert storm["evidence"]["annual_exceedance_probability"] == .01
    assert storm["evidence"]["confidence_interval"] == {"level":.9,"lower_mm":19,"upper_mm":21}
    integral=sum((item["end_s"]-item["start_s"])*item["rate_m_s"] for item in storm["intervals"])
    assert math.isclose(integral,storm["depth_m"],rel_tol=1e-12)


@pytest.mark.parametrize("argument,value",[
    ("duration_minutes",30),("return_period_years",20),("distribution","alternating"),
    ("antecedent_saturation",1.1),
])
def test_rejects_unsupported_design_controls(monkeypatch,argument,value):
    controls={"latitude": 0,"longitude": 0,"label": "Test","duration_minutes": 60,
                  "return_period_years": 100,"distribution": "uniform","antecedent_saturation": .25}
    controls[argument]=value
    monkeypatch.setattr(noaa_atlas14,"fetch",lambda *args,**kwargs:pytest.fail("must validate before network"))
    with pytest.raises(ValueError):noaa_atlas14.design_storm(**controls)
