"""Replay full-HLL boundary mass flux into graph flow; retain unmet outflow."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np

from scripts.run_momentum_boundary_diagnostic import GAUGES, ROOT, TIMES, geometry, metrics, model
from services.reference.compartment_flow_candidate import build_graph
from services.reference.exchange_replay_diagnostic import BoundaryRecordingHLL, ExchangeReplayGraph

sources=['scripts/run_boundary_exchange_replay.py','services/reference/exchange_replay_diagnostic.py',
         'scripts/run_momentum_boundary_diagnostic.py','services/reference/momentum_diagnostic.py',
         'services/reference/solver_segments_candidate.py','services/reference/compartment_flow_candidate.py']
protocol={"scope": 'Boundary mass-exchange replay, not prescribed boundary momentum',
    "declared_after_initial_ablation": True,"case": 'open_island',"grid_spacing_m": 1.,"duration_s": 180,"dt_max_s": .025,
    "exchange": 'Mean of both HLL RK stage mass fluxes, each fine boundary face, every actual timestep; same timestep for graph',
    "gates": {"max_boundary_flux_adjustment_m3_s": 1e-12,"max_storage_difference_m3": 1e-10,"mass_relative_max": 1e-10},
    "source_sha256": {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},"production_enabled": False}
pp=ROOT/'exchange-protocol.json';encoded=json.dumps(protocol,indent=2)
if pp.exists() and pp.read_text()!=encoded:raise ValueError('Frozen exchange protocol changed')
pp.write_text(encoded)
base,wall=model('open_island','hll_full')
hll=BoundaryRecordingHLL(base.surface,base.config,depth=base.u[...,0],coastal=base.coastal)
hll.open_rows=np.flatnonzero(~wall[:,0])
assert np.array_equal(hll.open_rows,np.flatnonzero(~wall[:,-1]))
z,_,initial,levels=geometry('open_island');graph=build_graph(z,wall,1)
s=ExchangeReplayGraph(graph,initial[~wall],{'west':lambda t:0.,'east':lambda t:0.},dt_max=.025)
# Validate record ordering explicitly rather than trusting graph enumeration.
for edge in ('west','east'):
    actual=[int(np.flatnonzero(graph.labels[:,0 if edge=='west' else -1]==a)[0]) for a,*_ in graph.boundary_faces[edge]]
    assert actual==hll.open_rows.tolist()
traces={'hll_full':[],'matched_exchange_graph':[]};volumes=[];maxdiff=0.;maxmass=0.;records=[]
for t in TIMES:
    while hll.time<t-1e-10:
        # HLL dt bound is conservative for the low-speed graph diagnostic here.
        dt=hll.step(min(hll.stable_dt(),s.dt_max,float(t)-hll.time))
        s.prescribed_boundary_q=hll.mean_boundary_q;s.step(dt)
        records.append([hll.time,dt,*hll.mean_boundary_q.tolist()])
        maxdiff=max(maxdiff,abs(hll.storage()-float(s.volume.sum())))
        maxmass=max(maxmass,hll.ledger()['relative_residual'],s.ledger()['relative_residual'])
    for name,h in [('hll_full',hll.u[...,0]),('matched_exchange_graph',s.fine_depth())]:
        traces[name].append([float(h[r,c]) for r,c in GAUGES])
    volumes.append({"time_s": t,"hll": hll.ledger(),"graph": s.ledger()})
    if t%60==0:print(json.dumps({"seconds_simulated": t,"max_storage_difference_m3": maxdiff,
                                    "max_flux_adjustment": s.max_boundary_flux_adjustment}),flush=True)
gates={"boundary_flux": s.max_boundary_flux_adjustment<=1e-12,"storage": maxdiff<=1e-10,"mass": maxmass<=1e-10}
old=json.loads((ROOT/'open_island-hll_full.json').read_text())
np.testing.assert_array_equal(traces['hll_full'],old['traces'])
result={"status": 'completed',"gates": gates,"matched_exchange_verified": all(gates.values()),
    "max_boundary_flux_adjustment_m3_s": s.max_boundary_flux_adjustment,"max_storage_difference_m3": maxdiff,
    "mass_relative_max": maxmass,"hll_recording_reproduces_prior": True,
    "gauges": metrics(np.asarray(traces['matched_exchange_graph']),np.asarray(traces['hll_full'])),"production_enabled": False}
(ROOT/'exchange-replay.json').write_text(json.dumps({"times_s": TIMES.tolist(),"traces": traces,"volume_ledgers": volumes,"result": result},indent=2))
np.savez_compressed(ROOT/'exchange-per-step.npz',records=np.asarray(records),boundary_rows=hll.open_rows)
print(json.dumps(result))
