# Isolated copy of solver.py SHA256 3d16c26692eb009ee13fbfc4b0eaf9df56f009136c16c1064c31c08408060f2d
"""Conservative 2-D HLL shallow-water reference; SI units and float64 state.

Hydrostatic reconstruction with side-specific pressure corrections. Each face
is computed once. Sources transfer mass into finite soil storage; they do not
erase water. This implementation is independently exercised before GPU use.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from services.api.contracts import SolverConfig, Storm
from services.reference.coastal import CoastalBoundary
from services.reference.coastal_segments import CoastalSegments

G = 9.80665
type Array = NDArray[np.float64]


def _slices(dimensions: int) -> list[slice | int]:
    return [slice(None)] * dimensions


class NumericalError(RuntimeError):
    pass


def minmod(a: Array, b: Array) -> Array:
    return np.where(a * b > 0, np.sign(a) * np.minimum(np.abs(a), np.abs(b)), 0)


@dataclass
class Surface:
    z: Array
    dx: float
    dy: float
    solid: NDArray[np.bool_] | None = None
    roughness: Array | float = .035
    infiltration_f0: Array | float = 0.
    infiltration_fc: Array | float = 0.
    infiltration_decay: Array | float = 1 / 3600
    recovery: Array | float = 1 / 86400
    soil_capacity: Array | float = 0.
    percolation: Array | float = 0.
    rain_weights: Array | None = None
    inflow_m3_s: Array | float = 0.
    inflow_start_s: Array | float = 0.
    inflow_end_s: Array | float = 0.
    outlet_tailwater: Array | float = -1e20
    outlet_crest: Array | float = 0.
    outlet_rate: Array | float = 0.
    outlet_capacity_m3_s: Array | float = 0.

    def __post_init__(self):
        self.z = np.asarray(self.z, dtype=np.float64).copy()
        if self.z.ndim != 2 or not np.isfinite(self.z).all() or min(self.dx, self.dy) <= 0:
            raise ValueError("Invalid terrain/grid")
        self.solid = np.zeros(self.z.shape, bool) if self.solid is None else np.asarray(self.solid, bool)
        if self.solid.shape != self.z.shape:
            raise ValueError("Mask/grid mismatch")
        for key in ("roughness", "infiltration_f0", "infiltration_fc", "infiltration_decay",
                    "recovery", "soil_capacity", "percolation", "outlet_crest", "outlet_rate", "outlet_capacity_m3_s", "inflow_m3_s", "inflow_start_s", "inflow_end_s"):
            value = np.broadcast_to(np.asarray(getattr(self, key), float), self.z.shape).copy()
            if not np.isfinite(value).all() or np.any(value < 0):
                raise ValueError(f"Invalid {key}")
            value[self.solid] = 0
            setattr(self, key, value)
        self.outlet_tailwater=np.broadcast_to(np.asarray(self.outlet_tailwater,float),self.z.shape).copy()
        if not np.isfinite(self.outlet_tailwater).all():raise ValueError('Invalid tailwater')
        if np.any((self.inflow_m3_s>0)&(self.inflow_end_s<=self.inflow_start_s)):raise ValueError('Invalid inflow interval')
        if np.any(self.infiltration_fc > self.infiltration_f0):
            raise ValueError("Horton final capacity exceeds initial capacity")
        if self.rain_weights is None:
            self.rain_weights = (~self.solid).astype(float)
        else:
            self.rain_weights = np.asarray(self.rain_weights, float).copy()
        if self.rain_weights.shape != self.z.shape or not np.isfinite(self.rain_weights).all():
            raise ValueError("Invalid rainfall allocation")
        if np.any(self.rain_weights < 0) or np.any(self.rain_weights[self.solid] != 0):
            raise ValueError("Rain cannot be applied inside solid cells")


class Solver:
    def __init__(self, surface: Surface, config: SolverConfig | None = None,
                 depth: Array | float = 0., saturation: float = 0.,
                 coastal: CoastalBoundary | CoastalSegments | None = None):
        self.surface = surface
        self.coastal = coastal
        self.coastal_segments = coastal.segments if isinstance(coastal, CoastalSegments) else (("coast", coastal),) if coastal else ()
        self.boundary_volumes = {name: [0., 0.] for name, _ in self.coastal_segments}
        self.boundary_fingerprint = CoastalSegments(self.coastal_segments).fingerprint()
        if coastal:coastal.validate(surface)
        self.config = config or SolverConfig()
        if not 0 <= saturation <= 1:
            raise ValueError("Saturation must be in [0,1]")
        self.u = np.zeros((*surface.z.shape, 3), dtype=np.float64)
        self.u[..., 0] = np.broadcast_to(depth, surface.z.shape)
        self.u[surface.solid] = 0
        if np.any(self.u[..., 0] < 0) or not np.isfinite(self.u).all():
            raise ValueError("Invalid initial depth")
        self.soil: Array = np.asarray(surface.soil_capacity, dtype=np.float64) * saturation
        self.wet_time = np.zeros(surface.z.shape)
        self.max_depth = self.u[..., 0].copy()
        self.time = 0.
        self.steps = 0
        self.initial_volume = self.storage()
        self.inflow_volume = 0.
        self.rain_volume = self.outflow_volume = self.deep_volume = 0.
        self.roundoff_volume = 0.
        self.min_dt, self.max_dt = float("inf"), 0.

    def storage(self) -> float:
        return float(np.sum(self.u[..., 0] + self.soil, dtype=np.float64) * self.surface.dx * self.surface.dy)

    def ledger(self) -> dict:
        residual = self.initial_volume + self.rain_volume + self.inflow_volume - self.storage() - self.outflow_volume - self.deep_volume
        return {"initial_m3": self.initial_volume, "rain_m3": self.rain_volume, "inflow_m3": self.inflow_volume,
                "stored_m3": self.storage(), "outflow_m3": self.outflow_volume,
                "deep_percolation_m3": self.deep_volume, "residual_m3": residual,
                "relative_residual": abs(residual) / max(self.initial_volume + self.rain_volume + self.inflow_volume, 1.),
                "roundoff_correction_m3": self.roundoff_volume}

    def stable_dt(self) -> float:
        h = self.u[..., 0]
        vel = np.divide(self.u[..., 1:], h[..., None], out=np.zeros_like(self.u[..., 1:]),
                        where=h[..., None] > self.config.dry_depth_m)
        c = np.sqrt(G * h)
        speed = (np.abs(vel[..., 0]) + c) / self.surface.dx + (np.abs(vel[..., 1]) + c) / self.surface.dy
        reservoir_speed=0.
        for _, boundary in self.coastal_segments:
            peak=max(k[1] for k in boundary.levels)
            lowest=min(self.surface.z.flat[i] for i in boundary.cells)
            reservoir_speed=max(reservoir_speed,np.sqrt(G*max(0.,peak-lowest))*(1/self.surface.dx+1/self.surface.dy))
        return min(self.config.dt_max_s, self.config.cfl / max(float(speed.max())+reservoir_speed, 1e-12))

    def _faces(self, state: Array, axis: int, boundary_time: float | None = None) -> tuple[Array, Array, Array, Array]:
        """Return shared flux, left/right bed corrections, internal bed source."""
        pad = [(0, 0), (0, 0)]
        pad[axis] = (1, 1)
        p = np.pad(state, pad + [(0, 0)], mode="edge")
        z = np.pad(self.surface.z, pad, mode="edge")
        mask = np.pad(self.surface.solid, pad, mode="edge")
        normal = 2 if axis == 0 else 1
        if self.config.boundary == "closed":
            lo, hi = _slices(3), _slices(3)
            lo[axis], hi[axis] = 0, -1
            lo[2] = hi[2] = normal
            p[tuple(lo)] *= -1
            p[tuple(hi)] *= -1
        else:
            # Transmissive outward-only boundaries: no undocumented inflow.
            lo, hi = _slices(3), _slices(3)
            lo[axis], hi[axis] = 0, -1
            lo[2] = hi[2] = normal
            p[tuple(lo)] = np.minimum(p[tuple(lo)], 0)
            p[tuple(hi)] = np.maximum(p[tuple(hi)], 0)
        left, right = _slices(2), _slices(2)
        left[axis], right[axis] = slice(None, -1), slice(1, None)
        l, r = tuple(left), tuple(right)
        pl, pr, zl, zr = p[l].copy(), p[r].copy(), z[l].copy(), z[r].copy()
        bed_source = np.zeros_like(state[..., 0])
        if self.config.spatial_order == 2:
            # Minmod reconstruction in free surface, bed and velocity.
            h = p[..., 0]
            vel = np.divide(p[..., 1:], h[..., None], out=np.zeros_like(p[..., 1:]),
                            where=h[..., None] > self.config.dry_depth_m)
            eta = h + z
            def slope(a):
                s = minmod(a - np.roll(a, 1, axis), np.roll(a, -1, axis) - a)
                edge0, edge1 = _slices(a.ndim), _slices(a.ndim)
                edge0[axis], edge1[axis] = 0, -1
                s[tuple(edge0)] = s[tuple(edge1)] = 0
                near_solid = mask | np.roll(mask, 1, axis) | np.roll(mask, -1, axis)
                s[near_solid] = 0
                return s
            sz, se, sv = slope(z), slope(eta), slope(vel)
            # Limit reconstructed water depths, retaining the common bed slope.
            sh = np.clip(se - sz, -2*h, 2*h)
            se = sz + sh
            zl, zr = z[l] + sz[l]/2, z[r] - sz[r]/2
            hl = np.maximum(eta[l] + se[l]/2 - zl, 0)
            hr = np.maximum(eta[r] - se[r]/2 - zr, 0)
            pl[..., 0], pr[..., 0] = hl, hr
            pl[..., 1:] = hl[..., None] * (vel[l] + sv[l]/2)
            pr[..., 1:] = hr[..., None] * (vel[r] - sv[r]/2)
            inner = _slices(2)
            inner[axis] = slice(1, -1)
            bed_source = -G * h[tuple(inner)] * sz[tuple(inner)]
        # Boundary ghost states must mirror the reconstructed fluid face. A
        # centre-based ghost leaves artificial wall flux when velocity slopes exist.
        low, high = _slices(2), _slices(2)
        low[axis], high[axis] = 0, -1
        low_index, high_index = tuple(low), tuple(high)
        pl[low_index], zl[low_index] = pr[low_index], zr[low_index]
        pr[high_index], zr[high_index] = pl[high_index], zl[high_index]
        if self.config.boundary == "closed":
            pl[..., normal][low_index] *= -1
            pr[..., normal][high_index] *= -1
        else:
            pl[..., normal][low_index] = np.minimum(pl[..., normal][low_index], 0)
            pr[..., normal][high_index] = np.maximum(pr[..., normal][high_index], 0)
        for _, boundary in self.coastal_segments:
            if axis == (1 if boundary.edge in ('west','east') else 0):
                level=boundary.level(self.time if boundary_time is None else boundary_time)
                ny,nx=self.surface.z.shape
                for i in boundary.cells:
                    row,col=divmod(i,nx)
                    negative=boundary.edge in ('west','south')
                    face=(row,0 if negative else nx) if axis==1 else (0 if negative else ny,col)
                    fluid=pr[face] if negative else pl[face]
                    bed=zr[face] if negative else zl[face]
                    h=max(0.,level-bed)
                    ghost=np.zeros(3);ghost[0]=h
                    if fluid[0]>self.config.dry_depth_m:ghost[1:]=fluid[1:]*h/fluid[0]
                    if negative:pl[face]=ghost
                    else:pr[face]=ghost
        ml, mr = mask[l], mask[r]
        # A wall reflects its fluid neighbour at identical bed elevation.
        pl[ml] = pr[ml]
        pl[..., normal][ml] *= -1
        zl[ml] = zr[ml]
        pr[mr] = pl[mr]
        pr[..., normal][mr] *= -1
        zr[mr] = zl[mr]
        h0l, h0r = pl[..., 0].copy(), pr[..., 0].copy()
        zstar = np.maximum(zl, zr)
        hl, hr = np.maximum(0, h0l + zl - zstar), np.maximum(0, h0r + zr - zstar)
        vl = np.divide(pl[..., 1:], h0l[..., None], out=np.zeros_like(pl[..., 1:]),
                       where=h0l[..., None] > self.config.dry_depth_m)
        vr = np.divide(pr[..., 1:], h0r[..., None], out=np.zeros_like(pr[..., 1:]),
                       where=h0r[..., None] > self.config.dry_depth_m)
        pl[..., 0], pr[..., 0] = hl, hr
        pl[..., 1:], pr[..., 1:] = vl * hl[..., None], vr * hr[..., None]
        ul, ur = vl[..., normal-1], vr[..., normal-1]
        fl, fr = pl * ul[..., None], pr * ur[..., None]
        fl[..., 0], fr[..., 0] = pl[..., normal], pr[..., normal]
        fl[..., normal] += .5 * G * hl**2
        fr[..., normal] += .5 * G * hr**2
        sl = np.minimum(np.minimum(ul - np.sqrt(G*hl), ur - np.sqrt(G*hr)), 0)
        sr = np.maximum(np.maximum(ul + np.sqrt(G*hl), ur + np.sqrt(G*hr)), 0)
        den = sr - sl
        flux = np.divide(sr[..., None]*fl - sl[..., None]*fr + (sl*sr)[..., None]*(pr-pl),
                         den[..., None], out=np.zeros_like(pl), where=den[..., None] > 1e-15)
        return flux, .5*G*(h0l**2-hl**2), .5*G*(h0r**2-hr**2), bed_source

    def rhs(self, state: Array, boundary_time: float | None = None) -> tuple[Array, float]:
        rhs = np.zeros_like(state)
        incoming=outgoing=0.
        segment_rates={name:[0.,0.] for name,_ in self.coastal_segments}
        for axis, spacing in ((0, self.surface.dy), (1, self.surface.dx)):
            flux, cl, cr, bed = self._faces(state, axis, boundary_time)
            lo, hi = _slices(2), _slices(2)
            lo[axis], hi[axis] = slice(None, -1), slice(1, None)
            l, r = tuple(lo), tuple(hi)
            rhs -= (flux[r] - flux[l]) / spacing
            normal = 2 if axis == 0 else 1
            rhs[..., normal] += (cr[l] - cl[r] + bed) / spacing
            # Integrate signed external face fluxes separately. A net outflow
            # ledger would hide simultaneous coastal inflow and return flow.
            low_faces=np.take(flux[...,0],0,axis=axis)
            high_faces=np.take(flux[...,0],-1,axis=axis)
            face_width=self.surface.dx if axis==0 else self.surface.dy
            for name, boundary in self.coastal_segments:
                if axis != (1 if boundary.edge in ('west','east') else 0):continue
                negative=boundary.edge in ('west','south')
                ny,nx=self.surface.z.shape
                for cell in boundary.cells:
                    row,col=divmod(cell,nx)
                    face=(row,0 if negative else nx) if axis==1 else (0 if negative else ny,col)
                    signed=float(flux[face][0])*face_width*(1 if negative else -1)
                    segment_rates[name][0]+=max(signed,0.)
                    segment_rates[name][1]+=max(-signed,0.)
            incoming+=float((np.maximum(low_faces,0).sum()+np.maximum(-high_faces,0).sum())*face_width)
            outgoing+=float((np.maximum(-low_faces,0).sum()+np.maximum(high_faces,0).sum())*face_width)
        rhs[self.surface.solid] = 0
        out = -float(rhs[..., 0].sum()) * self.surface.dx * self.surface.dy
        self._boundary_exchange=(incoming,outgoing)
        self._segment_rates=segment_rates
        return rhs, out

    def _check(self, value: Array) -> None:
        if not np.isfinite(value).all() or value[..., 0].min() < -1e-10:
            raise NumericalError("Non-finite or negative depth; reduce timestep, never clip material loss")

    def _sources(self, dt: float, rain: float) -> None:
        s = self.surface
        h = self.u[..., 0]
        if s.rain_weights is None:
            raise RuntimeError("Rainfall allocation was not initialized")
        added = rain * dt * s.rain_weights
        self.rain_volume += float(added.sum()) * s.dx * s.dy
        external=np.where((self.time>=s.inflow_start_s)&(self.time<s.inflow_end_s),s.inflow_m3_s,0)*dt/(s.dx*s.dy)
        self.inflow_volume+=float(external.sum())*s.dx*s.dy
        h += added + external
        wet = h > self.config.dry_depth_m
        capacity = s.infiltration_fc + (s.infiltration_f0-s.infiltration_fc)*np.exp(-s.infiltration_decay*self.wet_time)
        transfer = np.minimum(np.minimum(h, capacity*dt), np.maximum(0, s.soil_capacity-self.soil))
        factor = np.divide(h-transfer, h, out=np.zeros_like(h), where=h > 0)
        self.u[..., 1:] *= factor[..., None]
        h -= transfer
        self.soil += transfer
        deep = np.minimum(self.soil, s.percolation*dt)
        self.soil -= deep
        self.deep_volume += float(deep.sum()) * s.dx * s.dy
        self.wet_time = np.where(wet, self.wet_time+dt, self.wet_time*np.exp(-s.recovery*dt))
        drained = np.minimum(np.maximum(0, h-np.maximum(s.outlet_crest,s.outlet_tailwater-s.z))*(-np.expm1(-s.outlet_rate*dt)), s.outlet_capacity_m3_s*dt/(s.dx*s.dy))
        self.u[..., 1:] *= np.divide(h-drained, h, out=np.zeros_like(h), where=h>0)[..., None]
        h -= drained
        self.outflow_volume += float(drained.sum())*s.dx*s.dy
        qnorm = np.linalg.norm(self.u[..., 1:], axis=2)
        friction = 1 + dt * G * s.roughness**2 * qnorm / np.maximum(h, self.config.dry_depth_m)**(7/3)
        self.u[..., 1:] /= friction[..., None]
        self.u[self.surface.solid] = 0

    def step(self, dt: float, rain_m_s: float = 0.) -> float:
        if dt <= 0 or rain_m_s < 0:
            raise ValueError("Invalid timestep/forcing")
        for knot_values in [self.surface.inflow_start_s,self.surface.inflow_end_s]:
            knots = np.asarray(knot_values, dtype=np.float64)
            future=knots[knots>self.time+1e-7]
            if future.size:dt=min(dt,float(future.min())-self.time)
        if self.coastal:
            future=[t for _,boundary in self.coastal_segments for t,_ in boundary.levels if t>self.time+1e-7]
            if future:dt=min(dt,min(future)-self.time)
        self._sources(dt/2, rain_m_s)
        # Recompute stable bound after rain has activated formerly dry cells.
        if dt > self.stable_dt() * 1.01:
            raise NumericalError("Timestep exceeds post-source CFL bound")
        start = self.u.copy()
        r0, out0 = self.rhs(start,self.time+dt/2)
        exchange0=self._boundary_exchange
        rates0=self._segment_rates
        stage = start + dt*r0
        self._check(stage)
        r1, out1 = self.rhs(stage,self.time+dt/2)
        exchange1=self._boundary_exchange
        rates1=self._segment_rates
        self.u = .5 * (start + stage + dt*r1)
        self._check(self.u)
        tiny = np.minimum(self.u[..., 0], 0)
        self.roundoff_volume -= float(tiny.sum()) * self.surface.dx * self.surface.dy
        self.u[..., 0] = np.maximum(self.u[..., 0], 0)
        if self.coastal:
            self.inflow_volume+=dt*.5*(exchange0[0]+exchange1[0])
            self.outflow_volume+=dt*.5*(exchange0[1]+exchange1[1])
        else:
            self.outflow_volume += dt * .5 * (out0 + out1)
        for name in self.boundary_volumes:
            for k in (0,1):self.boundary_volumes[name][k]+=dt*.5*(rates0[name][k]+rates1[name][k])
        self._sources(dt/2, rain_m_s)
        self._check(self.u)
        self.time += dt
        self.steps += 1
        self.max_depth = np.maximum(self.max_depth, self.u[..., 0])
        self.min_dt, self.max_dt = min(self.min_dt, dt), max(self.max_dt, dt)
        return dt

    def checkpoint(self) -> dict:
        return {"version": "coastal-segments-experiment-1", "boundary_fingerprint":self.boundary_fingerprint, "boundary_volumes":{k:list(v) for k,v in self.boundary_volumes.items()}, "u": self.u.copy(), "soil": self.soil.copy(),
                "wet_time": self.wet_time.copy(), "max_depth": self.max_depth.copy(),
                **{k: getattr(self, k) for k in ("time", "steps", "initial_volume", "rain_volume",
                   "outflow_volume", "inflow_volume", "deep_volume", "roundoff_volume", "min_dt", "max_dt")}}

    def restore(self, checkpoint: dict) -> None:
        if checkpoint.get("version") != "coastal-segments-experiment-1" or checkpoint.get("boundary_fingerprint") != self.boundary_fingerprint or checkpoint["u"].shape != self.u.shape:
            raise ValueError("Incompatible checkpoint")
        for key, value in checkpoint.items():
            if key == "boundary_volumes":
                self.boundary_volumes={k:list(v) for k,v in value.items()}
            elif key not in ("version", "boundary_fingerprint"):
                setattr(self, key, value.copy() if isinstance(value, np.ndarray) else value)

    def advance(self, until: float, rain_m_s: float = 0.) -> None:
        while self.time < until - 1e-9:
            dt = min(self.stable_dt(), until-self.time)
            saved = self.checkpoint()
            for attempt in range(12):
                try:
                    self.step(dt, rain_m_s)
                    break
                except NumericalError:
                    self.restore(saved)
                    dt /= 2
            else:
                raise NumericalError("Step failed after twelve timestep reductions")

    def run(self, storm: Storm, cancelled=lambda: False):
        """Yield physical-time frames; exact knots preserve rainfall integral."""
        end = storm.duration_s + storm.recession_s
        yield self.frame()
        next_output = min(self.config.output_interval_s, end)
        knots = sorted(set([0., storm.duration_s, end] +
                           [t for i in storm.intervals for t in (i.start_s, i.end_s)]))
        while self.time < end - 1e-9:
            if cancelled():
                return
            rate = next((i.rate_m_s for i in storm.intervals if i.start_s <= self.time+1e-9 < i.end_s-1e-9), 0.)
            next_knot = next(t for t in knots if t > self.time+1e-9)
            self.advance(min(next_output, next_knot, end), rate)
            if self.time >= next_output-1e-9:
                yield self.frame()
                next_output = min(end, next_output+self.config.output_interval_s)

    def frame(self) -> dict:
        return {"time_s": self.time, "depth": self.u[..., 0].astype(np.float32),
                "max_depth": self.max_depth.astype(np.float32), "ledger": self.ledger(), "steps": self.steps}


def curve_number_excess(precipitation_m: float, curve_number: float, abstraction_ratio=.2) -> float:
    if precipitation_m < 0 or not 0 < curve_number <= 100 or not 0 <= abstraction_ratio <= 1:
        raise ValueError("Invalid CN inputs")
    retention = (25400/curve_number - 254)/1000
    initial = abstraction_ratio*retention
    if precipitation_m <= initial:
        return 0.
    return (precipitation_m-initial)**2/(precipitation_m+(1-abstraction_ratio)*retention)
