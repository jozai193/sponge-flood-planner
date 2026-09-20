"""Experimental local-inertial flow on connected subcell compartments.

Restricted to flat-bed channels bounded by permanent impermeable walls. Each
connected region inside a coarse cell has its own storage and water level.
Face widths count actual open fine-pixel contacts; enclosed pools stay separate.
This is not the production HLL solver, nor a general subgrid flood solver:
advection, overbank flow, internal bed sills, and turning losses are not modeled.
"""
from collections import deque
from dataclasses import dataclass

import numpy as np

G = 9.80665


@dataclass
class Graph:
    labels: np.ndarray
    area: np.ndarray
    bed: np.ndarray
    center: np.ndarray
    links: list
    boundary_faces: dict


def build_graph(bed, solid, factor, dx=1., dy=1.):
    z=np.asarray(bed,dtype=float);wall=np.asarray(solid,dtype=bool)
    if (z.ndim!=2 or z.shape!=wall.shape or not np.isfinite(z).all()
            or isinstance(factor,bool) or not isinstance(factor,int) or factor<1
            or any(n%factor for n in z.shape) or not np.isfinite([dx,dy]).all()
            or min(dx,dy)<=0):
        raise ValueError('Invalid fine terrain or grouping')
    ny,nx=z.shape;labels=np.full(z.shape,-1,dtype=int);regions=[]
    for r0 in range(0,ny,factor):
        for c0 in range(0,nx,factor):
            for r in range(r0,r0+factor):
                for c in range(c0,c0+factor):
                    if wall[r,c] or labels[r,c]>=0:continue
                    label=len(regions);cells=[];queue=deque([(r,c)]);labels[r,c]=label
                    while queue:
                        rr,cc=queue.popleft();cells.append((rr,cc))
                        for a,b in ((rr-1,cc),(rr+1,cc),(rr,cc-1),(rr,cc+1)):
                            if r0<=a<r0+factor and c0<=b<c0+factor and not wall[a,b] and labels[a,b]<0:
                                labels[a,b]=label;queue.append((a,b))
                    regions.append(np.asarray(cells))
    if not regions:raise ValueError('No open compartments')
    beds=[];areas=[];centers=[]
    for cells in regions:
        values=z[cells[:,0],cells[:,1]]
        if np.ptp(values)>1e-12:
            raise ValueError('Internal bed variation requires a sill/conveyance model; unsupported')
        beds.append(values[0]);areas.append(len(cells)*dx*dy)
        centers.append(((cells[:,1].mean()+.5)*dx,(cells[:,0].mean()+.5)*dy))
    centers=np.asarray(centers);contacts={}
    for r in range(ny):
        for c in range(nx):
            a=labels[r,c]
            if a<0:continue
            for rr,cc,axis,width in ((r,c+1,0,dy),(r+1,c,1,dx)):
                if rr>=ny or cc>=nx:continue
                b=labels[rr,cc]
                if b<0 or a==b:continue
                key=(int(a),int(b),axis)
                contacts[key]=contacts.get(key,0)+width
    links=[]
    for (a,b,axis),width in contacts.items():
        length=abs(centers[b,axis]-centers[a,axis])
        if length<=0:raise ValueError('Degenerate compartment distance')
        links.append((a,b,width,length,max(beds[a],beds[b])))
    faces={}
    for edge,cells,width,axis,position in (
        ('west',[(r,0) for r in range(ny)],dy,0,0),
        ('east',[(r,nx-1) for r in range(ny)],dy,0,nx*dx),
        ('south',[(0,c) for c in range(nx)],dx,1,0),
        ('north',[(ny-1,c) for c in range(nx)],dx,1,ny*dy)):
        counts={}
        for r,c in cells:
            a=int(labels[r,c])
            if a>=0:counts[a]=counts.get(a,0)+width
        faces[edge]=[(a,-1,w,abs(centers[a,axis]-position),beds[a]) for a,w in counts.items()]
    return Graph(labels,np.asarray(areas),np.asarray(beds),centers,links,faces)


class CompartmentFlow:
    def __init__(self,graph,stage,boundaries=None,roughness=.025,dt_max=.05):
        self.graph=graph;self.boundaries=boundaries or {}
        if not np.isfinite([roughness,dt_max]).all() or roughness<0 or dt_max<=0:
            raise ValueError('Invalid numerical configuration')
        self.roughness=roughness;self.dt_max=dt_max
        self.volume=np.maximum(np.broadcast_to(np.asarray(stage,dtype=float),graph.area.shape)-graph.bed,0)*graph.area
        if not np.isfinite(self.volume).all():raise ValueError('Invalid initial level')
        links=list(graph.links);forcing=[None]*len(links)
        for edge,function in self.boundaries.items():
            if edge not in graph.boundary_faces:raise ValueError('Invalid boundary edge')
            for face in graph.boundary_faces[edge]:links.append(face);forcing.append(function)
        data=np.asarray(links,dtype=float).reshape(-1,5)
        self.a=data[:,0].astype(int);self.b=data[:,1].astype(int)
        self.width=data[:,2];self.length=data[:,3];self.sill=data[:,4];self.forcing=forcing
        self.q=np.zeros(len(links));self.time=0.;self.steps=0
        self.initial=float(self.volume.sum());self.inflow=0.;self.outflow=0.
        self.limited_steps=0;self.max_froude=0.

    @property
    def stage(self):return self.graph.bed+self.volume/self.graph.area

    def ledger(self):
        residual=self.initial+self.inflow-self.outflow-float(self.volume.sum())
        return {'initial_m3': self.initial,'inflow_m3': self.inflow,'outflow_m3': self.outflow,
                    'stored_m3': float(self.volume.sum()),'residual_m3': residual,
                    'relative_residual': abs(residual)/max(1,self.initial+self.inflow)}

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
        froude=np.divide(np.abs(proposed),self.width*h*np.sqrt(G*h),out=np.zeros_like(proposed),where=active)
        self.max_froude=max(self.max_froude,float(froude.max(initial=0)))

    def advance(self,until):
        if not np.isfinite(until) or until<self.time:raise ValueError('Invalid end time')
        while self.time<until-1e-10:
            # Conservative graph wave-speed bound, including external reservoir levels.
            maxstage=max(float(self.stage.max()),*(float(f(self.time)) for f in self.boundaries.values())) if self.boundaries else float(self.stage.max())
            c=np.sqrt(G*max(maxstage-float(self.graph.bed.min()),1e-8))
            rates=np.bincount(self.a,weights=self.width*c,minlength=len(self.volume))
            inside=self.b>=0
            rates+=np.bincount(self.b[inside],weights=self.width[inside]*c,minlength=len(self.volume))
            bound=float(np.min(np.divide(.2*self.graph.area,rates,out=np.full_like(rates,np.inf),where=rates>0)))
            self.step(min(self.dt_max,bound,until-self.time))

    def fine_depth(self):
        labels=self.graph.labels
        return np.where(labels>=0,(self.volume/self.graph.area)[np.maximum(labels,0)],0.)
