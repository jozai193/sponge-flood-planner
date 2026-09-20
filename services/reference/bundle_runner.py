"""Bounded server CPU reference fallback for prepared rainfall-only bundles."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from services.api.contracts import CPUReferenceRequest, SolverConfig
from services.reference.solver import Solver, Surface


def run_bundle_reference(folder:Path,request:CPUReferenceRequest):
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'));grid=manifest['grid'];nx,ny=grid['nx'],grid['ny'];n=nx*ny
    if n>128*128:raise ValueError('CPU fallback is bounded to 128 x 128 prepared grids; choose a smaller grid without changing an existing result')
    if request.storm.duration_s+request.storm.recession_s>7200:raise ValueError('CPU fallback is bounded to a two-hour simulation window; WebGL or an offline reference job is required')
    def load(name,dtype):
        a=np.fromfile(folder/f'{name}.bin',dtype=dtype)
        if a.size!=n or (np.issubdtype(a.dtype,np.floating) and not np.isfinite(a).all()):raise ValueError(f'Invalid {name} bundle array')
        return a.reshape(ny,nx)
    z=load('z','<f4').astype(float);solid=load('solid','u1').astype(bool);roughness=load('roughness','<f4').astype(float);infiltration=load('infiltration','<f4').astype(float);capacity=load('soil_capacity','<f4').astype(float);weights=load('rain_weights','<f4').astype(float)
    surface=Surface(z=z,dx=grid['dx_m'],dy=grid['dy_m'],solid=solid,roughness=roughness,infiltration_f0=infiltration,infiltration_fc=infiltration,soil_capacity=capacity,rain_weights=weights)
    config=SolverConfig(engine='cpu-hll',spatial_order=1,dt_max_s=1,output_interval_s=max(1,min(60,(request.storm.duration_s+request.storm.recession_s)/120)))
    solver=Solver(surface,config,saturation=request.antecedent_saturation);frames=list(solver.run(request.storm));frame=frames[-1];ledger=frame['ledger'];area=surface.dx*surface.dy
    ledger['surface_m3']=float(solver.u[...,0].sum()*area);ledger['subsurface_m3']=float(solver.soil.sum()*area)
    return {'schema':'sponge.cpu-reference.v1','engine':'cpu-hll-float64','limitations':['Rainfall-only baseline reference; interventions, external inflows, outlets and coastal stages are not accepted by this endpoint.','Reference agreement does not establish observed flood accuracy.'],'bundle_id':manifest['bundle_id'],'grid':grid,'frame':{'time_s':frame['time_s'],'depth':frame['depth'].reshape(-1).tolist(),'maxDepth':frame['max_depth'].reshape(-1).tolist(),'ledger':ledger,'steps':frame['steps']}}
