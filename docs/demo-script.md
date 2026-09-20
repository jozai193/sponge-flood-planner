# SPONGE 4-minute demo script

Use the prepared Spring Garden bundle. Record at 1440 × 960 or 1920 × 1080. Keep the browser console closed and do not claim calibrated accuracy, monetary savings or grant eligibility.

## 0:00–0:30 — Problem, Earth Forward impact and product

“Urban stormwater decisions are often made from disconnected maps, spreadsheets and static reports. Philadelphia's green-infrastructure program shows the need for decentralized, creative planning in dense neighbourhoods. SPONGE turns sourced neighbourhood data into an interactive, reproducible screening workflow: configure a storm, watch water move, test green infrastructure, and export exactly what was simulated.”

Show the full 3D neighbourhood, source labels, mapped buildings and trees. Point out the visible “exploratory use only” status.

## 0:30–1:05 — Honest data and assumptions

Open **Data & assumptions**. Show the terrain/obstacle integrity check, source dates, attribution, unverified drainage and next-data requests.

“The demo bundle works without live GIS services. SPONGE separates software correctness from data coverage and observed accuracy. Missing inputs stay missing; it does not invent a sewer network, parcel ownership or building values.”

Close the panel.

## 1:05–1:45 — Live physics

Set 100 mm over one hour and click **Run storm**. Orbit the view while the clock advances. Show actual water-depth display, area above 10 cm and water-balance residual. Stop after visible flooding develops.

“This is a WebGL2 shallow-water simulation, not a prerecorded animation. The same engine is checked against a CPU reference, analytic controls, conservation cases, dry fronts and coastal grid refinement. The displayed residual is part of the result gate.”

## 1:45–2:35 — Intervention and planning

Select a candidate site, choose a rain garden, review the editable capacity/infiltration/cost assumptions, check **Assume this site is eligible**, and apply it. Mention that eligibility and cost are assumptions for this demo.

Click **Compare selected design** or **Plan with physics**. Show that the search evaluates bounded subsets against the same baseline forcing and can return no improvement. Do not call it AI or a global optimum.

“SPONGE supports rain gardens, bioswales, permeable pavement and detention basins. Storage is finite, saturation and overflow remain in the water ledger, and controls can return water to the surface or export it through an explicit outlet.”

## 2:35–3:20 — Before/after replay and evidence

In the comparison dialog, scrub the shared timeline. Show the highlighted intervention footprint and label in the planned view, then point to the live surface-water difference, water at intervention locations, improved/worsened area and per-intervention storage card. Explain that downward cues appear only when surface water and configured infiltration coexist, while an outlet trace shows a configured route rather than claiming a measured per-facility discharge. Show remaining flooding, local adverse changes if any, storage/outflow, assumed line-item cost and unchanged forcing identity.

Open the export controls and show the planning HTML, reproducible scenario JSON, selected-design GeoJSON, cost CSV and SHA-256 manifest.

“Every number comes from stored solver results. The green-infrastructure overlay explains the modelled mechanism, but it does not claim guaranteed prevention. The report rejects altered physics, stale hashes, incomplete storms, non-conservation and changed costs. Damage remains unavailable because this bundle has no defensible valuation inventory.”

## 3:20–4:00 — Reliability, learning and close

Briefly show restore controls or reload an interrupted storm.

“Flood simulation itself is not new—EPA SWMM and prior flood dashboards prove that. What I built differently is a judge-accessible chain from live browser physics, through finite intervention storage and robust budget search, to synchronized comparison and tamper-checked evidence. SPONGE runs without an account, recovers interrupted work, and ships as a hardened production container. The final suite passes 334 Python tests, 136 TypeScript tests and 46 real-browser and GPU tests.”

Add one truthful sentence in your own voice: what you knew before this event, what you had to learn, and which part stretched you most. If any code existed before August 21, disclose it here and on Devpost.

Close with: “SPONGE makes early stormwater tradeoffs visible and reproducible—while being explicit about the surveys and professional validation still needed before a real municipal decision.”

## Recording checklist

- Keep the final video between 3 and 5 minutes.
- Record a real non-default edit and live simulation.
- Do not splice a cached run so it appears live; label any replay.
- Include repository and live application links in the final card only after they exist.
- Add captions and verify that all source attributions remain readable.
- Do not submit `output/playwright/sponge-demo-4m59.webm` unchanged: it has no audio stream and does not clearly show a completed comparison/export.
