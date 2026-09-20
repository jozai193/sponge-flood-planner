"""Portable survey contracts. Imports retain provenance and never imply calibration."""
from datetime import datetime
from typing import Literal

from pydantic import Field, FiniteFloat, model_validator
from pyproj import CRS

from services.api.contracts import Storm, WireModel


class SurveySource(WireModel):
    title:str=Field(min_length=3,max_length=300)
    attribution:str=Field(min_length=3,max_length=500)
    observed_at:datetime
    horizontal_crs:str
    vertical_datum:str=Field(min_length=2,max_length=200)
    license:str=Field(min_length=2,max_length=300)
    provenance:Literal['surveyed','provider_estimate','user_assumption']

    @model_validator(mode='after')
    def valid_crs(self):
        CRS.from_user_input(self.horizontal_crs)
        if self.observed_at.tzinfo is None:raise ValueError('Observation timestamp needs a timezone')
        return self


class TerrainSource(SurveySource):
    surface_type:Literal['bare_earth','topobathymetry']='bare_earth'


class DrainNode(WireModel):
    id:str=Field(min_length=1,max_length=100)
    x:FiniteFloat
    y:FiniteFloat
    invert_m:FiniteFloat
    ground_m:FiniteFloat
    kind:Literal['inlet','junction','outfall']
    inlet_capacity_m3_s:FiniteFloat|None=Field(default=None,ge=0)
    tailwater_m:FiniteFloat|None=None
    storage_area_m2:FiniteFloat|None=Field(default=None,gt=0,le=10000)
    initial_depth_m:FiniteFloat=Field(default=0,ge=0,le=100)
    inlet_curve:list[tuple[FiniteFloat,FiniteFloat]]|None=Field(default=None,min_length=2,max_length=100)

    @model_validator(mode='after')
    def elevations(self):
        if self.invert_m>self.ground_m:raise ValueError('Node invert is above ground')
        if self.inlet_curve:
            if self.inlet_curve[0]!=(0,0):raise ValueError('Inlet head-flow curve must start at (0 m, 0 m3/s)')
            for previous,current in zip(self.inlet_curve,self.inlet_curve[1:]):
                if current[0]<=previous[0] or current[1]<previous[1] or current[1]<0:
                    raise ValueError('Inlet curve head must increase and discharge must not decrease')
        return self


class DrainPipe(WireModel):
    id:str=Field(min_length=1,max_length=100)
    from_node:str
    to_node:str
    diameter_m:FiniteFloat=Field(gt=0,le=30)
    length_m:FiniteFloat=Field(gt=0,le=100000)
    manning_n:FiniteFloat=Field(gt=0,le=1)


class DrainageSurvey(WireModel):
    kind:Literal['drainage']='drainage'
    source:SurveySource
    nodes:list[DrainNode]=Field(min_length=1,max_length=10000)
    pipes:list[DrainPipe]=Field(max_length=20000)

    @model_validator(mode='after')
    def topology(self):
        ids={n.id for n in self.nodes}
        if len(ids)!=len(self.nodes):raise ValueError('Duplicate node ID')
        if len({p.id for p in self.pipes})!=len(self.pipes):raise ValueError('Duplicate pipe ID')
        for p in self.pipes:
            if p.from_node not in ids or p.to_node not in ids:raise ValueError('Pipe references a missing node')
            if p.from_node==p.to_node:raise ValueError('Self-loop pipe')
        return self


class RainfallSurvey(WireModel):
    kind:Literal['rainfall']='rainfall'
    source:SurveySource
    storm:Storm


class VectorSurvey(WireModel):
    kind:Literal['waterways','catchments','buildings','landcover','observations']
    source:SurveySource
    features:list[dict]=Field(min_length=1,max_length=20000)

    @model_validator(mode='after')
    def geometries(self):
        import numpy as np
        from pyproj import Transformer
        from shapely import get_coordinates
        from shapely.geometry import shape
        transform=Transformer.from_crs(self.source.horizontal_crs,4326,always_xy=True)
        for f in self.features:
            geom=shape(f.get('geometry',{}))
            if geom.is_empty or not geom.is_valid:raise ValueError('Invalid survey geometry')
            coords=get_coordinates(geom)
            if not np.isfinite(coords).all():raise ValueError('Non-finite survey coordinates')
            lon,lat=transform.transform(coords[:,0],coords[:,1])
            if not np.isfinite(lon).all() or not np.isfinite(lat).all() or np.any(np.abs(lat)>90):
                raise ValueError('Survey CRS cannot transform geometry')
            props=f.get('properties',{})
            if self.kind=='observations':
                depth=props.get('depth_m')
                if not isinstance(depth,(int,float)) or not np.isfinite(depth) or depth<0:
                    raise ValueError('Flood observations require nonnegative depth_m')
            if self.kind=='landcover' and props.get('class_id') not in (10,20,30,40,50,60,70,80,90,95,100):
                raise ValueError('Land-cover polygons require a WorldCover-compatible class_id')
        return self


def validate_import(body):
    models={'drainage':DrainageSurvey,'rainfall':RainfallSurvey}
    return models.get(body.get('kind'),VectorSurvey).model_validate(body)
