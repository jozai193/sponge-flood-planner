"""Diagnostic only: replay per-face, per-step HLL mass exchange into graph flow.

Does not transfer HLL boundary momentum: graph momentum lives on faces rather
than cells. Exact exchange isolates mass forcing, not all boundary conditions.
"""
import numpy as np

from services.reference.compartment_flow_candidate import CompartmentFlow, G
from services.reference.momentum_diagnostic import MomentumDiagnosticSolver


class BoundaryRecordingHLL(MomentumDiagnosticSolver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.open_rows = np.array([], dtype=int)
        self.recorded_rhs_faces: list[np.ndarray] = []

    def rhs(self, state, boundary_time=None):
        result = super().rhs(state, boundary_time)
        self.recorded_rhs_faces.append(self.current_boundary_faces.copy())
        return result

    def _faces(self, state, axis, boundary_time=None):
        result = super()._faces(state, axis, boundary_time)
        if axis == 1:
            flux = result[0][..., 0]
            rows = self.open_rows
            # Graph boundary sign is positive outward, negative inward.
            self.current_boundary_faces = np.concatenate((-flux[rows, 0], flux[rows, -1]))*self.surface.dy
        return result

    def step(self, dt, rain_m_s=0.):
        self.recorded_rhs_faces = []
        actual = super().step(dt, rain_m_s)
        if len(self.recorded_rhs_faces) != 2:
            raise RuntimeError("Exchange diagnostic requires exactly two recorded right-hand faces")
        self.mean_boundary_q = .5*(self.recorded_rhs_faces[0]+self.recorded_rhs_faces[1])
        return actual


class ExchangeReplayGraph(CompartmentFlow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prescribed_boundary_q = None
        self.max_boundary_flux_adjustment = 0.

    def step(self,dt):
        if not np.isfinite(dt) or dt<=0:raise ValueError('Invalid timestep')
        eta=self.stage;left=eta[self.a];right=eta[np.maximum(self.b,0)].copy()
        for i,function in enumerate(self.forcing):
            if function is not None:right[i]=function(self.time+dt/2)
        if not np.isfinite(right).all():raise ValueError('Nonfinite boundary')
        h=np.maximum(np.maximum(left,right)-self.sill,0.)
        active=h>1e-8;unit=np.divide(self.q,self.width,out=np.zeros_like(self.q),where=self.width>0)
        proposed=np.zeros_like(self.q)
        # Local inertial momentum per unit width, semi-implicit Manning friction.
        proposed[active]=self.width[active]*(unit[active]+G*h[active]*dt*(left[active]-right[active])/self.length[active])/(1+G*dt*self.roughness**2*np.abs(unit[active])/h[active]**(7/3))
        if self.prescribed_boundary_q is not None:
            values = np.asarray(self.prescribed_boundary_q, dtype=float)
            if values.shape != proposed[self.b < 0].shape or not np.isfinite(values).all():
                raise ValueError('Invalid prescribed boundary discharge')
            proposed[self.b < 0] = values
        requested = proposed[self.b < 0].copy()
        donor=np.where(proposed>=0,self.a,self.b)
        outgoing=np.bincount(donor[donor>=0],weights=np.abs(proposed[donor>=0])*dt,minlength=len(eta))
        scales=np.ones(len(eta));need=outgoing>self.volume
        scales[need]=self.volume[need]*(1-1e-12)/outgoing[need]
        if np.any(need):self.limited_steps+=1
        proposed*=np.where(donor>=0,scales[np.maximum(donor,0)],1.)
        delta=np.bincount(self.a,weights=-proposed*dt,minlength=len(eta))
        inside=self.b>=0
        delta+=np.bincount(self.b[inside],weights=proposed[inside]*dt,minlength=len(eta))
        new=self.volume+delta
        if not np.isfinite(new).all() or np.any(new<0):raise FloatingPointError('Invalid volume; no clipping applied')
        boundary=proposed[~inside]*dt
        self.outflow+=float(boundary[boundary>0].sum());self.inflow-=float(boundary[boundary<0].sum())
        self.volume=new;self.q=proposed;self.time+=dt;self.steps+=1
        self.max_boundary_flux_adjustment = max(self.max_boundary_flux_adjustment,
            float(np.max(np.abs(proposed[self.b < 0]-requested), initial=0.)))
        froude=np.divide(np.abs(proposed),self.width*h*np.sqrt(G*h),out=np.zeros_like(proposed),where=active)
        self.max_froude=max(self.max_froude,float(froude.max(initial=0)))
