"""Experimental terrain storage curves; not a hydraulic solver.

Retain the elevations within each coarse cell rather than replacing them with
one elevation. Volumes assume a level water surface in each cell. They are
potential storage, not proof of hydraulic access or actual inundation.
"""
import numpy as np


class SubgridStorage:
    def __init__(self, fine_bed, factor, fine_dx, fine_dy):
        z = np.asarray(fine_bed, dtype=float)
        if (z.ndim != 2 or not np.isfinite(z).all() or isinstance(factor, bool)
                or not isinstance(factor, int) or factor <= 0
                or any(n % factor for n in z.shape)
                or not np.isfinite([fine_dx, fine_dy]).all()
                or min(fine_dx, fine_dy) <= 0):
            raise ValueError('Finite, aligned terrain and positive cell sizes required')
        self.shape = (z.shape[0]//factor, z.shape[1]//factor)
        self.pixel_area = fine_dx*fine_dy
        self.count = factor*factor
        self.beds = np.sort(z.reshape(self.shape[0], factor, self.shape[1], factor)
                            .transpose(0,2,1,3).reshape(*self.shape,self.count),axis=-1)
        self.prefix = np.cumsum(self.beds,axis=-1)
        before = np.concatenate([np.zeros((*self.shape,1)),self.prefix[...,:-1]],axis=-1)
        self.thresholds = self.pixel_area*(self.beds*np.arange(self.count)-before)

    def _field(self, value):
        a = np.broadcast_to(np.asarray(value,dtype=float),self.shape)
        if not np.isfinite(a).all(): raise ValueError('Finite cell values required')
        return a

    def volume(self, stage):
        eta = self._field(stage)
        return np.maximum(eta[...,None]-self.beds,0).sum(axis=-1)*self.pixel_area

    def wet_area(self, stage):
        eta = self._field(stage)
        return (eta[...,None]>self.beds).sum(axis=-1)*self.pixel_area

    def stage(self, volume):
        v = self._field(volume)
        if np.any(v<0): raise ValueError('Negative water volume')
        count = np.maximum(1,(v[...,None]>=self.thresholds).sum(axis=-1))
        sums = np.take_along_axis(self.prefix,(count-1)[...,None],axis=-1)[...,0]
        # Zero volume is represented by the lowest subpixel bed elevation.
        return (v/self.pixel_area+sums)/count
