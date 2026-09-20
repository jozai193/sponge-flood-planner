"""Experimental subcritical, wet characteristic wave boundary.

Incoming-wave stage is NOT an observed total gauge stage. The incoming Riemann
invariant describes a simple wave relative to a still background; the outgoing
invariant is supplied by the interior. See ANUGA Characteristic_wave_boundary:
https://anuga.readthedocs.io/en/develop/reference/generated/anuga.Characteristic_wave_boundary.html
Equations independently expressed here in terms of the two invariants.
"""
import math
from dataclasses import dataclass

import numpy as np

from services.reference.coastal import CoastalBoundary

G = 9.80665


@dataclass(frozen=True)
class CharacteristicBoundary(CoastalBoundary):
    background_stage_m: float = 0.
    signal_kind: str = 'incoming_wave_stage'

    def validate(self, surface):
        super().validate(surface)
        if self.signal_kind != 'incoming_wave_stage':
            raise ValueError('Total gauge stages are not incoming-wave forcing')
        if not math.isfinite(self.background_stage_m):
            raise ValueError('Finite background stage required')
        if any(self.background_stage_m <= surface.z.flat[i] for i in self.cells):
            raise ValueError('Characteristic boundary requires a wet background')
        if min(v for _,v in self.levels) <= max(surface.z.flat[i] for i in self.cells):
            raise ValueError('Dry incoming-wave states are unsupported')


def wave_ghost(fluid, bed, incoming_stage, background_stage, edge, dry_depth=1e-5):
    """Return conservative ghost state using outward-normal characteristic speeds.

Reject wet/dry and supercritical regimes requiring a different boundary closure.
Preserve tangential velocity; this is a locally one-dimensional approximation.
"""
    fluid=np.asarray(fluid,dtype=float)
    if fluid.shape!=(3,) or not np.isfinite(fluid).all() or not all(map(math.isfinite,[bed,incoming_stage,background_stage])):
        raise ValueError('Finite conservative state and stages required')
    if edge not in ('west','east','south','north'):
        raise ValueError('Unknown boundary edge')
    h=float(fluid[0]);h0=background_stage-bed;hw=incoming_stage-bed
    if min(h,h0,hw)<=dry_depth:
        raise ValueError('Wet characteristic boundary required')
    normal=1 if edge in ('west','east') else 2
    sign=-1 if edge in ('west','south') else 1
    velocity=fluid[1:]/h
    un=sign*fluid[normal]/h
    ci=math.sqrt(G*h);c0=math.sqrt(G*h0);cw=math.sqrt(G*hw)
    if abs(un)>=ci:
        raise ValueError('Subcritical interior required')
    outgoing=un+2*ci
    incoming=2*c0-4*cw
    cg=(outgoing-incoming)/4
    ug=(outgoing+incoming)/2
    if cg<=0 or abs(ug)>=cg:
        raise ValueError('Subcritical wet ghost required')
    hg=cg*cg/G
    ghost=np.r_[hg,hg*velocity]
    ghost[normal]=sign*ug*hg
    return ghost
