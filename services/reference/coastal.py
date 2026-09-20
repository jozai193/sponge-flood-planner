"""Explicit measured-level boundary for float64 verification."""
from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CoastalBoundary:
    edge: str
    cells: tuple[int, ...]
    levels: tuple[tuple[float, float], ...]
    datum: str
    source: str

    def validate(self, surface):
        if self.edge not in ('west','east','south','north') or not self.datum.strip() or not self.source.strip():
            raise ValueError('Explicit coastal edge, datum and source required')
        ny,nx=surface.z.shape
        if not self.cells or len(set(self.cells))!=len(self.cells):raise ValueError('Invalid coastal cells')
        for i in self.cells:
            if not isinstance(i,int) or not 0<=i<nx*ny or surface.solid.flat[i]:raise ValueError('Invalid coastal cell')
            row,col=divmod(i,nx)
            if not {'west':col==0,'east':col==nx-1,'south':row==0,'north':row==ny-1}[self.edge]:
                raise ValueError('Coastal cell is not on declared edge')
        a=np.asarray(self.levels,dtype=float)
        if a.ndim!=2 or a.shape[1]!=2 or not len(a) or not np.isfinite(a).all() or a[0,0]!=0 or np.any(np.diff(a[:,0])<=0):
            raise ValueError('Invalid coastal level knots')

    def level(self,time):
        a=np.asarray(self.levels)
        return float(np.interp(time,a[:,0],a[:,1]))

    def initial_depth(self,surface):
        self.validate(surface)
        ny,nx=surface.z.shape;level=self.level(0)
        eligible=(surface.z<level)&~surface.solid
        visited=np.zeros((ny,nx),dtype=bool);queue=deque()
        for i in self.cells:
            row,col=divmod(i,nx)
            if eligible[row,col]:visited[row,col]=True;queue.append((row,col))
        while queue:
            row,col=queue.popleft()
            for rr,cc in ((row-1,col),(row+1,col),(row,col-1),(row,col+1)):
                if 0<=rr<ny and 0<=cc<nx and eligible[rr,cc] and not visited[rr,cc]:
                    visited[rr,cc]=True;queue.append((rr,cc))
        return np.where(visited,level-surface.z,0.)
