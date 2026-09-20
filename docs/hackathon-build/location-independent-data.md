# Location-independent evidence pipeline

All locations use the same canonical projected-metre bundle, solver, intervention compiler and evidence audit. Regional data sources are adapters; city names must never select physical constants or validation thresholds. Greenwood Regency is a possible private test case, not a product dependency or public demo fixture.

Implemented: authenticated `GET /api/v1/bundles/{id}/audit` checks terrain/obstacle artifacts and explains terrain resolution, footprint completeness, height provenance, materials, drainage, catchment, parcel eligibility and observation gaps. The UI exposes the audit under Data & assumptions. The audit describes the immutable bundle, not current scenario edits. It does not label missing records as absence, infer materials from imagery or assert validation from conservation alone.

## Extension contract

Future surface, drainage and observation adapters must return coverage geometry, observation/retrieval date, attribution/licence, units, horizontal CRS, vertical datum, missing-data mask and measured/estimated provenance. Availability has four distinct outcomes: available, outside coverage, unavailable and unknown. Provider selection is spatial and capability-based; errors must not silently produce synthetic authoritative data.

Surface classification must retain class probabilities and source resolution, then apply documented regional parameter ranges with sensitivity runs. Drainage imports require topology, dimensions, invert elevations, outlet/tailwater conditions and capacity evidence before coupled simulation. An inlet location alone cannot establish capacity. Observations must describe event timing, rainfall and measurement uncertainty before scoring predictions.

New regional adapters should pass identical contract tests using northern/southern hemisphere locations and coverage boundaries. Site-specific observations are validation datasets, not solver branches. Benchmark results must separate geocoding, cold provider requests, cached preparation, first render and GPU simulation, recording extent, grid and device.

## Present limits

Building sources now use a shared spatial capability registry with full-extent containment and priority selection. Configured provider bounds are routing envelopes, not evidence of complete records. Other data capabilities still need registry adapters; worldwide data coverage is not established. Current coordinate input excludes polar latitudes beyond ±80; extents are limited to 2 km. Antimeridian-spanning requests and complete OSM relation footprints need further adapter work. Terrain native resolution can be unknown. Verified soils, pipe networks and observed flood calibration are not currently bundled. The Philadelphia building adapter is selected through the registry; street-context routing remains in the existing context implementation. Incomplete Overpass responses now fail explicitly instead of being accepted as missing buildings.
