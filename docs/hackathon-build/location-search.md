# Finding a neighbourhood

Search a place or address and optionally add a city, region or country. For
example, enter `ozone evergreen` with city `Bangalore`. The current map index
calls this complex **Ozone Evengreen Apartments**. Confirm the displayed city
and coordinates before selecting a result; fuzzy matches can be unrelated.

If a name is missing, copy coordinates from a map and paste **latitude,
longitude**, for example `12.9086945, 77.6625469`. Signed decimal coordinates
work without contacting a geocoding provider. An optional city hint is ignored
for coordinate input. No location is selected automatically.

Search accepts locations worldwide, including coordinates up to the poles.
Terrain preparation currently supports **80°S–80°N**; unsupported search results
remain visible with an explanation and cannot start preparation. A successful
lookup does not establish terrain availability, complete building coverage or
flood accuracy. There is no claim that every named address is indexed.

## Providers and operation

Name searches make at most one bounded request each to Photon and Nominatim.
Photon's fuzzy candidates remain visible even when Nominatim returns unrelated
exact matches. Coordinate duplicates are merged; source names and OSM
attribution are displayed. Provider failures produce a warning while retaining
results from the other provider. Empty results and failures have explicit UI
messages; editing a query cancels and discards its previous request.

These public endpoints require no paid subscription or API key for this small
interactive workflow. They are shared services with limits, not guaranteed
production infrastructure. There is no autocomplete, bulk lookup or background
search. Shared Redis gates allow one name search every two seconds and enforce
at least 1.1 seconds between requests to each provider. Each provider response
is bounded to 1 MB with a 10-second HTTP timeout. Search caches expire after
24 hours; existing terrain/scientific source caches keep their original policy.

Configure `SPONGE_PHOTON_URL` and `SPONGE_NOMINATIM_URL` on the server to switch
to compatible self-hosted/approved endpoints. An empty URL disables that
provider. Restart the API after changing configuration.

Policies checked on September 14, 2026:

- [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/)
- [Photon public service, limits and self-hosting](https://github.com/komoot/photon#demo-server)
- [OpenStreetMap attribution](https://www.openstreetmap.org/copyright)

## Verification

`python -m scripts.verify_location_search` checks three named locations against
broad expected coordinate bounds (Bengaluru, Tokyo, Cape Town), a coordinate
lookup, and an unsupported polar coordinate. Results are saved to
`artifacts/verification/location-search-v1/live-search.json`. This is a small
regression sample, not a worldwide coverage assessment.

Focused Python contracts test outages, malformed responses, duplicate results,
coordinate bounds, rate gating and expiring caches. The existing browser
location regression covers queued/offline preparation and duplicate prevention.
`scripts/verify_location_search_browser.js` is a Playwright CLI check for query
cancellation, empty results, outages, polar limits and the loaded Ozone scene.
