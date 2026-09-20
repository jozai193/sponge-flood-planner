# Location-independent data expansion

Open **Data & assumptions → Broaden neighbourhood data → Find additional data**. Jobs survive closing the panel. Each source reports availability separately; one failed adapter does not replace missing evidence with invented features. The base neighbourhood remains usable while acquisition runs.

## Implemented sources

| Capability | Acquisition | Use |
|---|---|---|
| Buildings | Overture Python client, bounded STAC/GeoParquet query with pinned release | Reconcile against existing footprints; keep existing geometry on substantial overlap; apply a new bundle revision |
| Terrain | Copernicus GLO-30 COG windows | Downloadable surface-elevation reference; not automatically substituted for bare earth |
| Land cover | ESA WorldCover 2021 v200 COG windows | Classes plus validity mask; optional explicit mapping to exploratory hydraulic presets |
| Soils | SoilGrids WCS, 0–5 cm sand/clay median and 5th/95th percentiles | Texture estimates and uncertainty; no automatic conversion to measured infiltration |
| Waterways | OSM Overpass with fallback endpoint | Mapped surface channels; no implied absence or pipe capacity |
| Rivers | Cached global HydroRIVERS v1 archive, bounded queries | Regional channel geometry and attributes; no assumed storm discharge |
| Catchments | Cached global HydroBASINS level 6, nine regional partitions | Regional catchment context, not an urban drainage delineation |
| Rainfall | NASA CMR IMERG Final V07 discovery for up to three selected dates | Catalog links; imports support actual time-varying rainfall for runs and comparisons |
| Recent classification | Dynamic World Earth Engine adapter | Mean class probabilities on a 10 m projected grid; requires configured access, not live-verified here |

The public data are acquired server-side; simulation still runs on the visitor's browser GPU. Raw dataset resolution, missing samples, source identifiers and retrieval evidence are retained. Revisions rebuild obstacle raster, roof rainfall allocation and candidate screening. Existing bundle and scenarios are not mutated. Existing building geometry wins reconciliation where intersection exceeds half the smaller footprint area; this is a conservative heuristic, not a guarantee of correct conflation. Counts before clipping can differ from rendered feature counts.

## Access and provisioning

The current local installation has the global HydroRIVERS archive and all nine level-6 basin archives cached. A new server can provision them once:

```powershell
.venv/Scripts/python.exe -m scripts.cache_hydrorivers
.venv/Scripts/python.exe -m scripts.cache_hydrobasins
```

These are sizeable server caches, not browser downloads. Dataset attribution accompanies extracts. Source artifacts are cached for one day per bundle/capability/request/adapter version. Raster access reads bounded native windows (maximum four million source pixels); enrichment subprocesses have a 180-second deadline each. API accepts one active enrichment job per session. Total area remains limited to 2 km and latitude ±80; wrapped antimeridian extents are not yet supported.

Dynamic World uses `SPONGE_EE_PROJECT` and optional `SPONGE_EE_CREDENTIALS_FILE` in `.env`, or existing application-default credentials. No credentials are shipped. Earth Engine account/project access and usage terms remain the operator's responsibility. Without configuration, the UI reports `needs_access`; WorldCover remains usable. NASA catalog access is public; protected granule downloads still require the user's Earthdata access. No account was created or paid service enabled.

## Portable imports

Download JSON Schemas from the panel's **Download survey formats** action. Source metadata includes title, attribution, timezone-aware observation date, horizontal CRS, vertical datum, licence and surveyed/estimated/assumed provenance.

- **Drainage:** nodes, invert/ground elevations, inlet capacities where supplied, outfall heads, pipes, lengths, diameters and roughness. Validates IDs and topology. Stored as evidence; no coupled pipe solver is implied.
- **Rainfall:** validated nonoverlapping intervals in metres/second with an integral matching event depth. **Use rainfall event** applies the exact intervals to ordinary GPU runs and physics comparisons. Editing rainfall controls returns to a custom uniform event.
- **Vector surveys:** building or land-cover polygons, waterways, catchments and depth observations. Stored as evidence; currently no automatic application/calibration of these vector imports.
- **Terrain:** source metadata JSON followed by a standalone single-band GeoTIFF, declared bare-earth elevation in metres. Requires CRS agreement and full grid coverage. Rebuilds a new bundle with the declared datum; no implicit vertical-datum offset is applied. Uploaded terrain changes invalidate prior scenario edits.

For Shapefile, GeoPackage and other GDAL-readable local vectors:

```powershell
.venv/Scripts/python.exe -m scripts.import_geodata survey.gpkg survey.json --kind waterways --source source.json --bbox 77.6 12.9 77.7 13.0
```

The bounding box is in the input dataset CRS. Feature imports are capped at 20,000. CSV rainfall uses columns `start_s,end_s,rate_mm_hr`:

```powershell
.venv/Scripts/python.exe -m scripts.import_geodata rainfall.csv rainfall.json --kind rainfall --source source.json
```

Downloaded IMERG V07 half-hourly HDF5 granules can be converted with `python -m scripts.import_imerg FILES --latitude LAT --longitude LON --source source.json --output rainfall.json`. The converter samples the nearest 0.1-degree pixel, checks units/dimension order and rejects missing samples, gaps and overlaps. Its parser is fixture-tested. Authenticated downloading is implemented through a server-side NASA Earthdata token; live credentialed access has not been verified locally.

## Verification and limits

Live reads succeeded for Overture (661 queried footprints on the Spring Garden sample), WorldCover, Copernicus, SoilGrids and NASA CMR (48 half-hourly records for 2024-08-01). Spring Garden channel queries returned zero intersecting records; that is not proof of no drainage. Both Sarjapur-area and Philadelphia bundles successfully sampled WorldCover/Copernicus and found a level-6 catchment. These are source-access checks, not a worldwide completeness survey.

WorldCover/Copernicus sampling took roughly 0.5–2.2 seconds in these local checks, excluding other sources and end-to-end acquisition. No universal loading-time or GPU-speed claim follows. Provider process shutdown initially hung on Windows after writing results; provider children atomically commit an attempt-specific result. The supervisor uses that file as its completion handshake and terminates lingering child processes instead of waiting on native teardown or inherited pipe handles. Timeout cleanup terminates the child tree. A regression test covers completed results with stalled teardown.

The land-cover mapping uses illustrative roughness/infiltration/storage presets. Detailed pavement permeability, soil compaction, underground pipes, channel bathymetry, first-floor elevations and event calibration still require additional evidence. The current audit and surface solver do not become an engineering-grade flood model simply by adding these datasets.

## Official references

- [Overture Python client](https://docs.overturemaps.org/getting-data/overturemaps-py/)
- [WorldCover open data](https://registry.opendata.aws/esa-worldcover-vito/)
- [Copernicus DEM](https://registry.opendata.aws/copernicus-dem/)
- [SoilGrids WCS](https://docs.isric.org/globaldata/soilgrids/wcs.html)
- [HydroRIVERS](https://www.hydrosheds.org/products/hydrorivers), [HydroBASINS](https://www.hydrosheds.org/products/hydrobasins)
- [NASA IMERG](https://gpm.nasa.gov/data/imerg)
- [Dynamic World](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1)

Final verification: the full authenticated acquisition job reported buildings, terrain, landcover, soils, waterways, hydrorivers and catchments available; rainfall catalog_only; Dynamic World needs_access. The fully cached rerun took 7.14 seconds locally. Browser tests passed for the main flow, isolated enrichment revisions/access controls, and rainfall import. Seven GPU tests, Python contract/numerics checks, TypeScript contract checks, production build and 13 schema checks passed.


## Remaining-limit work, September 11

NASA acquisition now downloads bounded IMERG V07 HDF5 granules when `SPONGE_EARTHDATA_TOKEN` is configured in the server `.env`. Obtain a user token through your existing Earthdata account; do not place it in a browser variable or paste it into chat. Restart the API and worker after local configuration. Select event dates and run acquisition; an available rainfall result exposes **Use acquired rainfall event**. Without a token, catalog discovery remains available. Redirects are restricted to NASA authentication/data hosts, cached files are checksum-verified, and invalid/login responses are rejected. Per-granule limit: 75 MB; event limit: 2 GB; download-provider deadline: 1,200 seconds. Large events can exceed these explicit budgets.

Dynamic World still needs an Earth Engine-enabled project and credentials: configure `SPONGE_EE_PROJECT` and either application-default credentials or `SPONGE_EE_CREDENTIALS_FILE`. Neither Earth Engine nor Earthdata access is configured on this machine. Existing WorldCover remains available without those accounts.

`services/reference/swmm_network.py` is an **experimental, isolated-process** SWMM 5.2.4 bridge using the native swmm-toolkit engine. It compiles circular conduits, outfalls and supplied inlet head-flow curves, with cell-sized surface storage interfaces. It is deliberately not wired into the production GPU solver: a startup transfer of 2.5 m3 was integrated as 2.375 m3, exposing a 0.125 m3 interface error. The diagnostic regression preserves evidence of this unresolved issue, rather than asserting conservation. Fractional coupling windows are rejected because the toolkit stride takes integer seconds. Two-way exchange, reverse-flow validation and combined water-budget closure remain required before enabling it. Imported drainage topology therefore still does not affect displayed floods.

New checks cover NASA redirects, cache corruption, authentication failure, invalid HDF5 responses, credential-free catalog fallback, inlet-curve validation and the experimental SWMM discrepancy. The acquired-rainfall browser test uses a mocked provider result; it does not prove live NASA download access.


### Credentialed verification update

After local Google login and NASA dataset agreement acceptance, Earth Engine returned 484 valid Dynamic World label samples in a Philadelphia test region. NASA delivered a 7,872,640-byte IMERG V07B HDF5 granule for 2024-08-01 00:00 UTC; the existing converter validated its 1,800-second rainfall interval. This verifies one real granule, not a full event acquisition. Current NASA catalog URLs use data.gesdisc.earthdata.nasa.gov and redirect to d2b3c3wh8s6en5.cloudfront.net. The downloader permits that CDN only after a trusted NASA redirect and omits the bearer token there; signed CDN URLs are not persisted in source metadata. Seven downloader tests pass. Earlier notes about missing local credentials are superseded by this verification. Drainage coupling remains experimental.


### Full event pipeline verification

A real session-owned API acquisition for Spring Garden on 2024-08-06 completed with both rainfall and Dynamic World available. Rainfall: 48 contiguous half-hour intervals, 86,400 seconds, 1.405 mm nearest-pixel total; cold acquisition 163.47 seconds. Dynamic World: 5.58 seconds, 100% valid sample coverage in the queried grid. These timings are local measurements, not global guarantees. The browser recovered a second real acquisition and selected it using Use acquired rainfall event, showing 1,440 minutes of rainfall and a 1,500-minute simulation window. No provider response was mocked; browser session bootstrap was routed to the test's actual API session. The full-day GPU simulation was not run in this check.

Satellite observations now use a preceding 90-day window ending at the rainfall event end (today if no event), rather than requiring imagery on the storm day. Exact imagery window remains in evidence provenance; zero valid cloud-free coverage is rejected. This avoids a storm-day image gap without implying that satellite cover is contemporaneous with flooding. Dynamic World remains evidence only, not automatic hydraulic material classification. A regression test covers the independent observation window, and duplicate React sibling keys in the data panel were fixed.


### Terrain and long-event validation work

Added provider-independent terrain diagnostics to the data audit: source elevation range (restoring the bundle's common offset), relief, vertical datum, depression spill storage and depth, and building-enclosed cells for which no domain-edge spill path is established. A four-neighbour priority flood computes diagnostics without modifying the solver elevation array. Domain edges are diagnostic exits only, not verified drainage outlets. Spring Garden reports 14.256 m relief and 1.831 m deepest mapped depression; this does not establish source accuracy. Curbs, raised plots, ramps and retaining walls still require adequate bare-earth survey detail and compatible datums.

New tests verify downhill transport, water retained below surrounding raised ground, exact simple-bowl storage, common vertical-offset invariance, no terrain mutation, and exclusion of building-enclosed cells from spill-storage estimates. All 56 Python contract/numerics tests pass. The real 24-hour rainfall plus one-hour recession GPU run was started in the browser, but has not completed verification; fixed small steps make long events slow. No drainage conservation fix or full-day validation is claimed by this update.
