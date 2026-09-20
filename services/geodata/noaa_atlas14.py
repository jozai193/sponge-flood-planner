"""NOAA Atlas 14 point-precipitation adapter and explicit design-storm shaping.

Atlas 14 provides total point precipitation depths, not a site-calibrated
hyetograph or areal rainfall field.  We therefore preserve the returned
estimate and confidence interval verbatim and label the temporal pattern as a
SPONGE modelling assumption.
"""
from __future__ import annotations

import ast
import math
import re
from typing import Literal

from services.geodata.providers import fetch

PFDS_URL = "https://hdsc.nws.noaa.gov/cgi-bin/new/cgi_readH5.py"
PFDS_PAGE = "https://hdsc.nws.noaa.gov/pfds/"

# Row and column order documented by the PFDS tabular product.  This adapter
# intentionally exposes only practical sub-day durations supported by the UI.
DURATION_ROWS = {10: 1, 60: 4, 360: 7}
RETURN_PERIOD_COLUMNS = {1: 0, 2: 1, 5: 2, 10: 3, 25: 4, 50: 5, 100: 6, 200: 7, 500: 8}
Distribution = Literal["uniform", "centered", "front_loaded", "rear_loaded"]
WEIGHTS: dict[str, tuple[int, ...]] = {
    "uniform": (1,) * 12,
    "centered": (1, 1, 2, 3, 5, 8, 8, 5, 3, 2, 1, 1),
    "front_loaded": (8, 7, 6, 5, 4, 3, 3, 2, 2, 1, 1, 1),
    "rear_loaded": (1, 1, 1, 2, 2, 3, 3, 4, 5, 6, 7, 8),
}


def _assignment(text: str, name: str):
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*(.+?);\s*$", text)
    if not match:
        raise ValueError(f"NOAA response is missing {name}")
    try:
        return ast.literal_eval(match.group(1))
    except (ValueError, SyntaxError) as exc:
        raise ValueError(f"NOAA response contains invalid {name}") from exc


def parse_pfds(text: str) -> dict:
    """Parse the bounded PFDS assignment response without executing it."""
    if len(text) > 1_000_000:
        raise ValueError("NOAA response exceeds the supported size")
    tables = {name: _assignment(text, name) for name in ("quantiles", "lower", "upper")}
    parsed: dict[str, list[list[float]]] = {}
    for name, table in tables.items():
        if not isinstance(table, list) or len(table) != 19:
            raise ValueError(f"NOAA {name} table has an unsupported shape")
        values = []
        for row in table:
            if not isinstance(row, list) or len(row) != 9:
                raise ValueError(f"NOAA {name} table has an unsupported shape")
            numeric = [float(value) for value in row]
            if any(not math.isfinite(value) or value < 0 for value in numeric):
                raise ValueError(f"NOAA {name} table contains an invalid value")
            values.append(numeric)
        parsed[name] = values
    scalars = {name: str(_assignment(text, name)) for name in
               ("lat", "lon", "region", "volume", "version", "authors", "unit", "ser", "datatype")}
    if scalars["unit"] != "metric" or scalars["ser"] != "ams" or scalars["datatype"] != "depth":
        raise ValueError("NOAA returned a different precipitation product")
    return {**parsed, **scalars}


def _intervals(depth_m: float, duration_s: int, distribution: Distribution) -> list[dict[str, float]]:
    weights = WEIGHTS[distribution]
    seconds = duration_s / len(weights)
    total = sum(weights)
    intervals = []
    for index, weight in enumerate(weights):
        start = index * seconds
        end = (index + 1) * seconds
        intervals.append({"start_s": start, "end_s": end,
                          "rate_m_s": depth_m * weight / total / seconds})
    return intervals


def design_storm(*, latitude: float, longitude: float, label: str,
                 duration_minutes: int, return_period_years: int,
                 distribution: Distribution, antecedent_saturation: float) -> dict:
    if duration_minutes not in DURATION_ROWS:
        raise ValueError("Supported NOAA durations are 10, 60 and 360 minutes")
    if return_period_years not in RETURN_PERIOD_COLUMNS:
        raise ValueError("Unsupported NOAA Atlas 14 return period")
    if distribution not in WEIGHTS:
        raise ValueError("Unsupported temporal rainfall distribution")
    if not 0 <= antecedent_saturation <= 1:
        raise ValueError("Antecedent saturation must be between 0 and 1")
    raw, source = fetch(PFDS_URL, {
        "lat": f"{latitude:.6f}", "lon": f"{longitude:.6f}", "type": "pf",
        "data": "depth", "units": "metric", "series": "ams",
    }, max_bytes=1_000_000, timeout_s=30, max_age_s=30 * 86400)
    try:
        data = parse_pfds(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("NOAA returned an unreadable response") from exc
    row, column = DURATION_ROWS[duration_minutes], RETURN_PERIOD_COLUMNS[return_period_years]
    estimate_mm = data["quantiles"][row][column]
    lower_mm, upper_mm = data["lower"][row][column], data["upper"][row][column]
    if not lower_mm <= estimate_mm <= upper_mm:
        raise ValueError("NOAA confidence interval does not contain the estimate")
    duration_s = duration_minutes * 60
    source_id = f"noaa-atlas14-volume-{data['volume']}-version-{data['version']}"
    pattern_label = {
        "uniform": "uniform",
        "centered": "SPONGE centered-block synthetic pattern",
        "front_loaded": "SPONGE front-loaded synthetic pattern",
        "rear_loaded": "SPONGE rear-loaded synthetic pattern",
    }[distribution]
    return {
        "schema_version": "sponge.v1",
        "name": f"NOAA Atlas 14 {return_period_years}-year {duration_minutes}-minute point precipitation",
        "duration_s": duration_s,
        "recession_s": 3600,
        "depth_m": estimate_mm / 1000,
        "intervals": _intervals(estimate_mm / 1000, duration_s, distribution),
        "return_period_years": return_period_years,
        "source_ids": [source_id],
        "distribution": pattern_label,
        "antecedent_saturation": antecedent_saturation,
        "evidence": {
            "provider": "NOAA National Weather Service Hydrometeorological Design Studies Center",
            "product": "NOAA Atlas 14 point precipitation frequency estimate",
            "source_url": source["source_url"],
            "product_page": PFDS_PAGE,
            "retrieved_at": source["retrieved_at"],
            "source_sha256": source["sha256"],
            "location": {"label": label, "latitude": float(data["lat"]), "longitude": float(data["lon"])},
            "region": data["region"], "volume": data["volume"], "version": data["version"],
            "authors": data["authors"], "series": "annual maximum series",
            "annual_exceedance_probability": 1 / return_period_years,
            "estimate_mm": estimate_mm,
            "confidence_interval": {"level": 0.90, "lower_mm": lower_mm, "upper_mm": upper_mm},
            "spatial_support": "Point estimate; not an areal rainfall field.",
            "temporal_distribution_source": f"{pattern_label}; NOAA supplies the total depth, not this interval pattern.",
            "stationarity_note": "Atlas 14 frequency estimates are historical stationary-frequency products; consider future NOAA Atlas 15 information when available.",
        },
    }
