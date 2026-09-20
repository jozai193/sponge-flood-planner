# Release performance evidence

The machine-readable profile is `artifacts/verification/release-performance.json`. It identifies the Windows device, CPU, RAM, installed Chrome, NVIDIA renderer, viewport, prepared-load samples, a real provider-backed production address journey, a current 128 × 128 GPU simulation, replay delivery, production API latency and one-shot API-container memory.

The measurements do **not** prove the original 500 × 500 / one-hour reference target. The current four-second controlled 128 × 128 simulation took about five seconds, and robust planning executes multiple complete storms. SPONGE therefore does not advertise an eight-second planning result. The UI reports each alternative and storm being evaluated and supports cancellation.

Replay retained all 121 synchronized states in order with no interval over twice its 150 ms delivery target. Earlier orbit measurements recorded near-7 ms RAF cadence on the installed NVIDIA Chrome path, but RAF cadence and callback/fence observations are not display presentation timestamps. A general 60 fps claim remains unproven.

Reproduce the current profile while the production stack is listening on port 18080 and Vite is listening on port 5173:

```powershell
node scripts/benchmark-replay.mjs
node scripts/summarize-release-performance.mjs
```

Performance targets are product targets, not correctness gates. Numerical resolution, timestep limits and source inputs are never silently reduced to meet them.
