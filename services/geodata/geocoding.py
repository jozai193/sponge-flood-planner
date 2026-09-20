"""Explicit worldwide place searches; search coverage is not terrain coverage.

Public service policies (reviewed 2026-09-14):
https://operations.osmfoundation.org/policies/nominatim/
https://github.com/komoot/photon#demo-server
No autocomplete or bulk queries. The API enforces shared provider rate limits.
"""
from __future__ import annotations

import json
import math
import re
from concurrent.futures import ThreadPoolExecutor

import httpx

from services.geodata.currency import currency_for_country
from services.geodata.providers import fetch

PAIR = re.compile(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*,\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*")
ATTRIBUTION = "© OpenStreetMap contributors"


def location(label, latitude, longitude, provider, country_code=None):
    lat, lon = float(latitude), float(longitude)
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Use latitude between -90 and 90 and longitude between -180 and 180")
    supported = -80 <= lat <= 80
    code = str(country_code).strip().upper() if country_code else None
    currency = currency_for_country(code)
    return {"label": str(label), "latitude": lat, "longitude": lon, "provider": provider,
            "country_code": code if code and len(code) == 2 else None,
            "currency": currency or "USD",
            "currency_source": "country" if currency else "fallback",
            "terrain_supported": supported,
            "coverage_note": "Terrain availability and quality are checked when loading." if supported else
                "Location found, but terrain outside 80°S–80°N is not supported yet."}


def coordinate_result(query):
    match = PAIR.fullmatch(query)
    if match is None:
        return None
    lat, lon = map(float, match.groups())
    return {"locations": [location(f"{lat:g}, {lon:g}", lat, lon, "Coordinates")],
            "attribution": "User-entered coordinates", "warnings": [], "sources": []}


def search_places(query, *, nominatim_url, photon_url, allow_request, fetcher=None):
    """One request per configured provider, with bounded bytes, age and timeout.

    Keep fuzzy candidates visible even when an exact geocoder returns plausible
    but unrelated results. Users must select a result; never silently pick one.
    """
    fetcher = fetcher or fetch

    def search_one(provider, url):
        if not url:
            return [], None, None
        if not allow_request(provider):
            return [], None, f"{provider} is busy. Wait a moment before searching again."
        params = {"q": query, "limit": 6}
        if provider == "Nominatim":
            params["format"] = "jsonv2"
            params["addressdetails"] = 1
        try:
            raw, source = fetcher(url, params, max_bytes=1_000_000, timeout_s=10, max_age_s=86400)
            data = json.loads(raw)
            rows = data if provider == "Nominatim" else data["features"]
            if not isinstance(rows, list):
                raise TypeError("Invalid search response")
            found = []
            for row in rows[:6]:
                try:
                    if provider == "Nominatim":
                        found.append(location(row["display_name"], row["lat"], row["lon"], provider,
                                              (row.get("address") or {}).get("country_code")))
                    else:
                        p = row["properties"]
                        if not isinstance(p, dict):
                            continue
                        parts = [p.get(k) for k in ("name", "housenumber", "street", "locality", "district", "city", "county", "state", "postcode", "country")]
                        label = ", ".join(dict.fromkeys(str(v) for v in parts if v))
                        if not label or row["geometry"]["type"] != "Point":
                            continue
                        lon, lat = row["geometry"]["coordinates"][:2]
                        found.append(location(label, lat, lon, provider, p.get("countrycode")))
                except (KeyError, TypeError, ValueError, IndexError):
                    continue
            return found, {**source, "provider": provider}, None
        except (httpx.HTTPError, OSError, KeyError, TypeError, ValueError):
            return [], None, f"{provider} is temporarily unavailable. You can still use coordinates."

    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(search_one, name, url) for name, url in
                (("Photon", photon_url), ("Nominatim", nominatim_url))]
        results = [job.result() for job in jobs]
    locations, seen = [], set()
    for rows, _, _ in results:
        for row in rows:
            key = (round(row["latitude"], 5), round(row["longitude"], 5))
            if key not in seen:
                seen.add(key)
                locations.append(row)
    return {"locations": locations[:10], "attribution": ATTRIBUTION,
            "sources": [source for _, source, _ in results if source],
            "warnings": [warning for _, _, warning in results if warning]}
