# Location loading benchmark — 2026-09-10

Three samples per prepared neighbourhood, 1440 × 960 headless Chromium, local Vite development server, local API, retained backend/provider caches. No other test suite ran during these samples. Renderer reported SwiftShader (software WebGL), not the laptop NVIDIA GPU.

| Location | Navigation to first scene callback (median) | Navigation to street-context UI ready (median) |
|---|---:|---:|
| Spring Garden, Philadelphia | 0.68 s | 2.24 s |
| Rittenhouse, Philadelphia | 0.67 s | 2.49 s |

Scene callback measurement covers a completed deck render callback observed by browser automation, not a GPU-fence measurement or network-only timing. Street-context ready is the UI state after context fetch; it does not prove all pixels have completed GPU execution. RAF cadence was around 59–60 Hz in these samples, but RAF is scheduling cadence, not a verified draw-throughput or storm-simulation benchmark. Do not advertise 60 FPS based on it.

Prepared scene load depends on geometry, grid size and device/browser. Preparing a new address additionally downloads and processes geodata; cold preparation time was not measured here. Prior OSM context requests timed out at around the provider timeout rather than completing, so arbitrary-location load latency has no demonstrated upper bound. Current geographic scope tested is two Philadelphia examples, not global coverage.

Reproduce: `node scripts/benchmark-locations.mjs`. Full samples: `artifacts/verification/location-speed.json`.


## 12 September landscape context measurements

Direct Python context calls with provider disk caches retained, two calls per location. These measure context generation, not complete browser rendering or cold address preparation. The second call uses the in-process WorldCover raster cache.

| Location | First call | Repeat | Trees | Water cells |
|---|---:|---:|---:|---:|
| Greenwood Regency | 6.629 s | 0.100 s | 1,194 | 0 |
| Chennai coast | 1.957 s | 0.038 s | 24 | 1,006 |
| Philadelphia | 0.883 s | 0.247 s | 760 | 6 |

All three returned 100% WorldCover coverage in these samples. Tree totals combine mapped inventory and illustrative classified-cover instances; they are not surveyed totals. Raw data: artifacts/verification/landscape-timings.json. Overpass calls now use 15-second client timeouts and a 10-second query budget per endpoint; two providers are attempted, and landscape generation remains independent after map failure. These are per-operation timeout controls, not a hard whole-request deadline.


## Prepared landscape browser benchmark — 12 September

Three samples per location, fresh browser context, 1440 × 960 Chromium, local Vite development server, SwiftShader software WebGL. Real prepared arrays and generated context were supplied through browser test routes; context generation, API latency, provider downloads and satellite imagery were excluded. No other test suite ran during these nine samples.

| Location | First scene callback (median) | Controls ready (median) | Trees | Water cells |
|---|---:|---:|---:|---:|
| Greenwood Regency | 0.85 s | 5.34 s | 1194 | 0 |
| Chennai coast | 0.83 s | 4.73 s | 24 | 1006 |
| Philadelphia | 0.87 s | 6.39 s | 760 | 6 |

These are browser-observed callbacks and UI readiness, not GPU fence timings, FPS, real GPU performance, or new-address preparation. Context counts verify supplied data, not independent visual fidelity. The several-second interval after the initial scene warrants profiling; no particular rendering stage has yet been established as its cause.

Reproduce: run `python -m scripts.prepare_landscape_benchmark <bundle IDs>` before `node scripts/benchmark-prepared-landscapes.mjs <same IDs>`. The IDs and all raw samples are in `artifacts/verification/prepared-landscape-speed.json`. Fixture generation is separate because synchronous Python invocation from the Node benchmark timed out even after producing output; the standalone preparation command completed successfully.


## Follow-up after terrain mesh reuse

Nine fresh samples with the same prepared location fixtures and software WebGL; no concurrent test suite. In-page mutation/long-task observers are now present, unlike the original benchmark, and intervening application changes exist. This is NOT an isolated A/B experiment.

| Location | First scene | Controls enabled in page | Controls observed by automation |
|---|---:|---:|---:|
| Greenwood Regency | 0.94 s | 2.93 s | 6.16 s |
| Chennai coast | 0.99 s | 2.78 s | 5.40 s |
| Philadelphia | 1.01 s | 3.81 s | 7.12 s |

No wall-time improvement demonstrated: automation-observed medians are slower than the earlier run. The code avoids a redundant terrain mesh rebuild, but neither causation of the slowdown nor a user-perceived gain is established. Original results preserved in artifacts/verification/prepared-landscape-speed-before-mesh-reuse.json; follow-up results in artifacts/verification/prepared-landscape-speed.json.


## Installed Chrome / Intel hardware acceleration

Ran the same nine prepared-data samples using installed Chrome, without ignore-gpu-blocklist or forced-renderer flags. Every canvas reported Intel UHD Graphics via ANGLE Direct3D11. The machine also has an NVIDIA RTX 5050, but this run did not use it.

| Location | Controls observed median | Slowest sample |
|---|---:|---:|
| Greenwood Regency | 0.90 s | 5.13 s |
| Chennai coast | 0.83 s | 0.86 s |
| Philadelphia | 0.99 s | 1.02 s |

The first sample took 5.13 seconds; the other eight took 0.80–1.02 seconds. Fresh page contexts share a browser process, so GPU/driver caches can remain warm. This supports a warm hardware rendering path, not an all-load subsecond promise. Browser version/backend changes confound direct causal comparisons with bundled SwiftShader. Initial graphics setup is a candidate cause of the first-load stall, not proven by this measurement. Provider/API latency, imagery and FPS remain excluded. Reproduce with SPONGE_BROWSER=chrome and the existing benchmark command; evidence: artifacts/verification/prepared-landscape-hardware-speed.json.


## NVIDIA preference and verification

User requested dedicated GPU use. Set current-user high-performance app preferences for installed Chrome, Codex executable and its WebView runtime, preserving previous values in artifacts/verification/gpu-preferences-before.json. Fresh Chrome reports RTX 5050 / Direct3D11. Existing in-app browser adapter is not yet verified and may require restarting Codex. Nine NVIDIA prepared samples: median controls ready Greenwood 1.03 s, Chennai 0.93 s, Philadelphia 1.01 s; first sample 3.60 s. Synthetic orbit RAF p95 about 7.1 ms in all samples; this is scheduling cadence, not a 140 FPS graphics claim. Four controlled coastal/replay tests passed in 36.4 s. API was offline during tests, so this does not establish live readiness. Artifacts: prepared-landscape-nvidia-speed.json and nvidia-validation.json.
