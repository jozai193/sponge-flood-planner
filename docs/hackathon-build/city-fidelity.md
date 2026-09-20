# Real-city fidelity: requirements and evidence

Checked 2026-09-11. Exact appearance and building heights are an explicit outstanding user requirement. Dense footprint extrusion does not fulfil it.

## Current scene

Prayagraj bundle `18fed01cabb1bba38caeb77f17a4705987f22e3b00e05db8979f7e6c34ef05fc` has 2,373 buildings after clipping the acquired 2,432 Overture features. All heights are assumed 9 m; no source-reported heights or floor counts were supplied. Source-footprint accuracy and completeness have not been independently checked. Facades and roof styling are illustrative. The scene is not a textured city reconstruction.

## Official provider evidence

- Google Photorealistic 3D Tiles supports textured 3D visualization using the OGC 3D Tiles format: https://developers.google.com/maps/documentation/tile/3d-tiles-overview
- Google coverage table has a single mark for India in Map Tiles 2D / 3D and a dash for Maps JavaScript 3D, whereas 3D-covered countries have two marks in the former. This does not establish Prayagraj 3D coverage; an API-key integration alone cannot satisfy the requirement: https://developers.google.com/maps/coverage
- MapmyIndia advertises 3D and 360-degree mapping. Its general product page does not prove textured, building-level coverage, heights, capture date, licensing or an accessible feed for the selected Prayagraj square: https://www.mapmyindia.com/map-data/
- Google Map Tiles policies restrict non-visualization uses including geodata extraction, image analysis and machine interpretation. A Google visual layer must not become a source of extracted hydraulic terrain or building heights: https://developers.google.com/maps/documentation/tile/policies

No commercial account, billing plan, terms agreement or external inquiry was created.

## Evidence required before claiming completion

1. A licensed dataset covering the entire selected domain, including capture date, coordinates, vertical reference and permitted visualization/analysis uses.
2. Textured geometry reflecting actual roofs and facades; identify missing or low-detail tiles explicitly.
3. Building heights with source metadata and stated uncertainty. A visual mesh alone is not a survey certificate.
4. Confirm ground registration and vertical alignment independently before overlaying simulated water. Keep hydraulic terrain independently sourced where analysis rights or accuracy are absent.
5. Verify a distributed sample of actual buildings against independent reference observations, and check missing coverage across the full domain.
6. Test level-of-detail streaming, loss of network access, stale scene switching, attribution, camera alignment and performance on the user's hardware.

## Next implementation path

Acquire a verified licensed Prayagraj 3D Tiles or georeferenced textured model source. Use a renderer appropriate to its format, retain attribution, and register it to the existing local metric grid. Surveyed building geometry/height imports remain a separate analytical path. Do not substitute random heights, AI-invented facades or satellite textures stretched onto walls as completion of the exact-replica requirement.


## Rendering and source-height improvement, September 12

The Philadelphia importer previously ignored the municipal `approx_hgt` field. The official footprint layer documents measurements in feet. The adapter now converts that field to metres and labels it as an approximate provider height, not an independently verified survey. `base_elevation` is not substituted for the solver terrain datum. Invalid/missing heights retain the explicit fallback. Processor 0.4.1 produces a new immutable bundle; older bundles are retained.

Prepared Spring Garden bundle: `2c607f51e1a064fc76ee6f5585cbc343358d0e9a39ead1a2806643e21cae37ba`. It contains 688 source footprints, 686 approximate provider heights and 2 assumed heights. Open with `http://127.0.0.1:5173/?bundle=2c607f51e1a064fc76ee6f5585cbc343358d0e9a39ead1a2806643e21cae37ba`. Explicit bundle links retain normal backend access checks.

The Philadelphia context path now loads the municipal 2025 tree inventory instead of omitting all vegetation when municipal roads are used. The checked sample contains 742 mapped tree positions. Canopy shape, crown size and tree height are illustrative; satellite vegetation outside this inventory is not reconstructed. Oversized/incomplete inventory responses fail visibly; provider failure retains the road context.

Mapped trees use instanced solid trunks and multi-lobed shaded crowns with upright orientation. Ground and satellite surfaces share continuous display interpolation, eliminating the disconnected cell surfaces; analytical elevations are unchanged. Satellite lift is reduced from 6 cm to 1 mm. Model view adds directional shadows (Eco disables them). Satellite mode uses imagery illumination to avoid adding duplicate cast shadows.

Satellite mode projects overhead imagery onto simplified flat roof surfaces, respecting polygon holes; facade windows remain illustrative. This is overhead texture projection, not photogrammetric roof or facade reconstruction. Capture dates, parallax and source alignment can differ. Both replay views use the same rendering path. The original exact-city requirement remains incomplete, especially for Prayagraj, where these Philadelphia-specific height and tree sources do not apply.

Official sources:
- https://services.arcgis.com/fLeGjb7u4uXqeF9q/ArcGIS/rest/services/Building_Footprints/FeatureServer/0
- https://opendataphilly.org/datasets/philadelphia-tree-inventory/
- https://services.arcgis.com/fLeGjb7u4uXqeF9q/ArcGIS/rest/services/ppr_tree_inventory_2025/FeatureServer/0

Verification artifacts: `output/playwright/upgraded-city.png`, `output/playwright/continuous-terrain.png`, `output/playwright/storm-visual-pass.png`. These show local browser rendering, not site accuracy or a hardware performance benchmark. A live 100 mm/10-minute exploratory storm was inspected during computation; this is visual QA, not a new scientific validation case.


## General landscape context (12 September)

All locations now attempt ESA WorldCover 2021 tree cover and permanent water context independently of mapped street/tree availability. The native source is 10 m classification, CC BY 4.0 (https://esa-worldcover.org/en/data-access). Illustrative tree placements are deterministic, exclude buffered source buildings, mapped roads and inventory trees, and have an 8,000-instance upper budget. They are explicitly distinguished from surveyed/mapped tree nodes. Invalid pixels never become trees or water. Provider failures preserve the other available layers and show coverage status. Successful raster windows are held in a bounded in-process cache.

Permanent water is rendered in both model and satellite modes through the shared live/replay scene. It is terrain-draped display context, not an ocean surface datum, bathymetry, initial solver water or wave forcing. Coastal flooding and tsunami propagation are NOT validated/implemented by this display change. A scientifically meaningful coastal scenario still requires compatible coastal terrain/bathymetry, datum, sea-level or wave boundary forcing and appropriate numerical validation.

Live data check: Greenwood Regency in Bengaluru produced 1,194 illustrative trees after mapped-road/building exclusions; the browser side view confirmed raised crowns. Chennai coast at 13.05, 80.283 returned 1,006 permanent-water cells in a 600 m context query. Coverage/classification date and limits are exposed in the app. Location selection also updates the bundle URL so reload does not revert to an earlier shared location.

Browser verification also confirmed visible coastal water in the Chennai model view, bundle de83f948c9e1a979adc1f4cfcfffbf63c2a9b9535527f53cb27d8aa4e7ee88b1. The 10 m classification produces a coarse shoreline; it is not a surveyed coastline. Current candidate screening and hydraulic materials still do not incorporate this display-only water classification.
