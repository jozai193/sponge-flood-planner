# Scenario composition — first v2 runtime increment

Implemented September 14, 2026. In **Flood scenario → Combined flood sources**,
rainfall, external inflow and prescribed coastal water levels can be enabled
independently. All four previous presets remain available.

`packages/domain/scenario.ts` owns the versioned forcing composition, legacy
preset mapping, storm clock and execution checks. `scenario-input.ts` compiles
the selected water sources into the existing GPU input; `App.tsx` uses the same
composed storm for ordinary runs, checkpoints and planner comparisons.

Each enabled source retains its own timing. A longer coastal series extends
recession, not rainfall duration: it cannot dilute or repeat the rain. Combined
coastal runs include at least 600 seconds after the final coastal knot. The final
coastal level holds thereafter. External inflow runs through its declared end;
the four legacy clock formulas are preserved exactly.

Coastal and inflow edge controls are separate. Incomplete active sources, no
enabled sources, and external inflows on coastal boundary cells are rejected
before worker execution. Overlap currently requires selecting another edge;
there is no implicit double-source policy. Outlets remain explicit configured
parameters. Existing water masks still govern eligible coastal cells.

## Verification

- 59 TypeScript contract/optimizer tests pass, including ten scenario composition
  checks. Legacy executable hashes and storm configurations match all four old
  presets; disabled sources do not leak into execution.
- Three controlled float64 reference runs exercise rain + inflow + coast, inflow
  + coast and rain + coast with the same terrain and coastal series.
- GPU/CPU maximum depth discrepancy is below 0.0000005 m in these small controlled
  cases. GPU relative mass residual is below 0.000001 (0.0001%). All three restart
  depth arrays match uninterrupted runs exactly. These are numerical parity
  checks, not observed flood accuracy or broad convergence claims.
- The actual comparison worker completes a 610-second all-source case with 121
  paired frames. A five-second rainfall event contributes 0.24 m³ exactly to
  floating-point tolerance; it is not stretched across the coastal recession.
  A no-design comparison is identical. The report builder verifies the result;
  exported inputs retain coastal levels and inflow, and exported storm retains rain.
- Four existing location/report browser regressions pass, including exact coastal
  export reruns. CLI UI checks pass for source toggles, missing/empty source errors,
  independent edge selection and restoration of the original rainfall preset.
- Typecheck/build pass. The existing large frontend chunk warning remains.
- All five frozen production solver/worker source hashes are unchanged.

Evidence: [structured numerical results](../../artifacts/verification/scenario-composition-v1/results.json),
[CPU reference](../../artifacts/verification/scenario-composition-v1/cpu-reference.json),
[GPU/planner/export log](../../artifacts/verification/scenario-composition-v1/gpu-check.log),
[UI log](../../artifacts/verification/scenario-composition-v1/ui-check.log).
Reproduce with `python -m scripts.verify_composed_reference`, then the Playwright
CLI scripts `scripts/verify_composed_gpu.js` and `scripts/verify_composed_ui.js`
against the running local app. The UI script restores rainfall after checking.

Docker startup encountered the known inaccessible `sailor-ingest.sock` again.
The existing guarded repair script backed up/recreated runtime socket directories;
engine 29.7.2 and the normal app services recovered without resetting stored data.

## Remaining architecture work

This is the **forcing-composition portion** of architecture v2, not the complete
cross-engine `ScenarioSpecV2` wire schema. The established executable input and
storm schemas/hashes still own arrays, recovery and report identity. Existing saved
scenarios need no destructive rewrite. New saved UI contexts retain the combined
mode and explicit component booleans.

The subsequent [shared Python/TypeScript contract](scenario-contract-v2.md) now
includes domain, datum, source and engine capability assessment. Physical data
admission remains pending. Engine adapters, admitted spatial
coastal boundary series, SWMM coupling, SFINCS comparisons and new observed-event
validation remain pending. No specialized engine was installed or activated by
this increment. General flood accuracy remains unvalidated.
