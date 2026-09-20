"""Diagnostic HLL momentum ablation; never production-enabled.

The face routine is copied from solver_segments_candidate.py; only momentum
advection and corresponding characteristic speeds are switchable. Reconstruction,
wall/ghost construction, sources, friction and integration remain inherited.
Different PDE boundary fluxes can result even with the same ghost construction.
"""
import numpy as np

from services.reference.solver_segments_candidate import Array, G, Solver, minmod


class MomentumDiagnosticSolver(Solver):
    def __init__(self, *args, advective_momentum=True, **kwargs):
        if not isinstance(advective_momentum, bool):
            raise TypeError('Momentum switch must be boolean')
        self.advective_momentum = advective_momentum
        super().__init__(*args, **kwargs)

    def _faces(self, state: Array, axis: int, boundary_time: float | None = None) -> tuple[Array, Array, Array, Array]:
        """Return shared flux, left/right bed corrections, internal bed source."""
        pad = [(0, 0), (0, 0)]
        pad[axis] = (1, 1)
        p = np.pad(state, pad + [(0, 0)], mode="edge")
        z = np.pad(self.surface.z, pad, mode="edge")
        mask = np.pad(self.surface.solid, pad, mode="edge")
        normal = 2 if axis == 0 else 1
        if self.config.boundary == "closed":
            lo, hi = [slice(None)] * 3, [slice(None)] * 3
            lo[axis], hi[axis] = 0, -1
            lo[2] = hi[2] = normal
            p[tuple(lo)] *= -1
            p[tuple(hi)] *= -1
        else:
            # Transmissive outward-only boundaries: no undocumented inflow.
            lo, hi = [slice(None)] * 3, [slice(None)] * 3
            lo[axis], hi[axis] = 0, -1
            lo[2] = hi[2] = normal
            p[tuple(lo)] = np.minimum(p[tuple(lo)], 0)
            p[tuple(hi)] = np.maximum(p[tuple(hi)], 0)
        left, right = [slice(None)] * 2, [slice(None)] * 2
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
                edge0, edge1 = [slice(None)] * a.ndim, [slice(None)] * a.ndim
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
            inner = [slice(None)] * 2
            inner[axis] = slice(1, -1)
            bed_source = -G * h[tuple(inner)] * sz[tuple(inner)]
        # Boundary ghost states must mirror the reconstructed fluid face. A
        # centre-based ghost leaves artificial wall flux when velocity slopes exist.
        low, high = [slice(None)] * 2, [slice(None)] * 2
        low[axis], high[axis] = 0, -1
        low, high = tuple(low), tuple(high)
        pl[low], zl[low] = pr[low], zr[low]
        pr[high], zr[high] = pl[high], zl[high]
        if self.config.boundary == "closed":
            pl[..., normal][low] *= -1
            pr[..., normal][high] *= -1
        else:
            pl[..., normal][low] = np.minimum(pl[..., normal][low], 0)
            pr[..., normal][high] = np.maximum(pr[..., normal][high], 0)
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
        if self.advective_momentum:
            fl, fr = pl * ul[..., None], pr * ur[..., None]
            sl = np.minimum(np.minimum(ul - np.sqrt(G*hl), ur - np.sqrt(G*hr)), 0)
            sr = np.maximum(np.maximum(ul + np.sqrt(G*hl), ur + np.sqrt(G*hr)), 0)
        else:
            # Local-inertial PDE: F=(qn, g*h*h/2, 0) in normal coordinates.
            # Its eigenvalues are +/-sqrt(g*h), 0, without a velocity shift.
            fl, fr = np.zeros_like(pl), np.zeros_like(pr)
            speed = np.maximum(np.sqrt(G*hl), np.sqrt(G*hr))
            sl, sr = -speed, speed
        fl[..., 0], fr[..., 0] = pl[..., normal], pr[..., normal]
        fl[..., normal] += .5 * G * hl**2
        fr[..., normal] += .5 * G * hr**2
        den = sr - sl
        flux = np.divide(sr[..., None]*fl - sl[..., None]*fr + (sl*sr)[..., None]*(pr-pl),
                         den[..., None], out=np.zeros_like(pl), where=den[..., None] > 1e-15)
        return flux, .5*G*(h0l**2-hl**2), .5*G*(h0r**2-hr**2), bed_source
