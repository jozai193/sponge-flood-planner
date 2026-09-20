"""Validated physical inputs. Exported JSON Schema is the browser wire contract."""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Grid(WireModel):
    nx: int = Field(ge=4, le=2048)
    ny: int = Field(ge=4, le=2048)
    dx_m: FiniteFloat = Field(gt=0, le=1000)
    dy_m: FiniteFloat = Field(gt=0, le=1000)
    crs: str = "LOCAL_METRES"
    origin_x_m: FiniteFloat = 0
    origin_y_m: FiniteFloat = 0
    elevation_origin_m: FiniteFloat = 0
    row_direction: Literal["north"] = "north"
    vertical_datum: str = "unspecified"


class RainInterval(WireModel):
    start_s: FiniteFloat = Field(ge=0)
    end_s: FiniteFloat = Field(gt=0)
    rate_m_s: FiniteFloat = Field(ge=0, le=0.001)

    @model_validator(mode="after")
    def interval(self):
        if self.end_s <= self.start_s:
            raise ValueError("Rain interval must have positive duration")
        return self


class Storm(WireModel):
    schema_version: Literal["sponge.v1"] = "sponge.v1"
    name: str = Field(min_length=1, max_length=200)
    duration_s: FiniteFloat = Field(gt=0, le=172800)
    recession_s: FiniteFloat = Field(ge=0, le=172800)
    depth_m: FiniteFloat = Field(ge=0, le=3)
    intervals: list[RainInterval] = Field(min_length=1, max_length=10000)
    return_period_years: FiniteFloat | None = Field(default=None, gt=0)
    source_ids: list[str] = Field(default_factory=list)
    distribution: str = "user-supplied"
    antecedent_saturation: FiniteFloat = Field(default=0.25, ge=0, le=1)

    @model_validator(mode="after")
    def integral(self):
        end, volume = 0.0, 0.0
        for item in self.intervals:
            if item.start_s < end or item.end_s > self.duration_s:
                raise ValueError("Rain intervals overlap or exceed storm duration")
            end = item.end_s
            volume += (item.end_s - item.start_s) * item.rate_m_s
        if abs(volume - self.depth_m) > max(1e-9, self.depth_m * 1e-4):
            raise ValueError("Rainfall integral does not equal declared event depth")
        return self


class SolverConfig(WireModel):
    engine: Literal["cpu-hll", "webgl2-hll"] = "cpu-hll"
    version: Literal["0.1.0"] = "0.1.0"
    cfl: FiniteFloat = Field(default=0.4, gt=0, le=0.45)
    dt_max_s: FiniteFloat = Field(default=1.0, gt=0, le=10)
    dry_depth_m: FiniteFloat = Field(default=1e-5, gt=0, le=0.001)
    spatial_order: Literal[1, 2] = 1
    boundary: Literal["closed", "open"] = "closed"
    output_interval_s: FiniteFloat = Field(default=60, gt=0, le=3600)


class Intervention(WireModel):
    id: str = Field(min_length=1, max_length=100)
    kind: Literal["rain_garden", "bioswale", "permeable_pavement", "detention_basin"]
    cells: list[int] = Field(min_length=1, max_length=100000)
    excavation_m: FiniteFloat = Field(default=0, ge=0, le=3)
    conductivity_m_s: FiniteFloat = Field(default=0, ge=0, le=0.001)
    storage_depth_m: FiniteFloat = Field(default=0, ge=0, le=2)
    roughness: FiniteFloat = Field(default=0.08, gt=0, le=0.5)
    percolation_m_s: FiniteFloat = Field(default=0, ge=0, le=0.001)
    cost_minor: int = Field(ge=0)
    eligibility: Literal["confirmed", "user_assumed", "unverified"] = "unverified"
    source_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_cells(self):
        if len(set(self.cells)) != len(self.cells):
            raise ValueError("Intervention contains duplicate cells")
        return self


class Design(WireModel):
    schema_version: Literal["sponge.v1"] = "sponge.v1"
    interventions: list[Intervention] = Field(default_factory=list, max_length=100)
    budget_minor: int = Field(default=200_000_000, ge=0)
    currency: Literal["USD"] = "USD"
    price_year: int = Field(default=2026, ge=2000, le=2100)
    locked_ids: list[str] = Field(default_factory=list)
    excluded_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def feasible(self):
        occupied: set[int] = set()
        ids: set[str] = set()
        for item in self.interventions:
            if item.id in ids or occupied.intersection(item.cells):
                raise ValueError("Duplicate or overlapping interventions")
            if item.eligibility == "unverified":
                raise ValueError("Site eligibility must be confirmed or explicitly assumed")
            ids.add(item.id)
            occupied.update(item.cells)
        if not set(self.locked_ids).issubset(ids):
            raise ValueError("Locked selections are missing")
        if ids.intersection(self.excluded_ids):
            raise ValueError("Excluded selection present")
        if sum(item.cost_minor for item in self.interventions) > self.budget_minor:
            raise ValueError("Design exceeds budget")
        return self


class PrepareRequest(WireModel):
    longitude: FiniteFloat = Field(ge=-180, le=180)
    latitude: FiniteFloat = Field(ge=-80, le=80)
    extent_m: int = Field(default=600, ge=100, le=2000)
    grid_cells: int = Field(default=128, ge=32, le=512)
    source: Literal["auto", "terrarium", "usgs_1m"] = "auto"
    label: str = Field(default="Selected neighbourhood", max_length=160)


class PlanningRequest(WireModel):
    bundle_id: str
    candidate_ids: list[str] = Field(max_length=200)
    budget_minor: int = Field(ge=0)
    locked_ids: list[str] = Field(default_factory=list)
    excluded_ids: list[str] = Field(default_factory=list)
    source_references: list[str] = Field(default_factory=list, max_length=200)
    intent: str = Field(default="Reduce neighbourhood flooding", max_length=2000)
    evaluation_feedback: list[dict] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def constraints(self):
        ids=set(self.candidate_ids)
        if len(ids)!=len(self.candidate_ids):raise ValueError("Duplicate catalogue IDs")
        if not set(self.locked_ids).issubset(ids) or not set(self.excluded_ids).issubset(ids):raise ValueError("Constraints reference unknown catalogue IDs")
        if set(self.locked_ids).intersection(self.excluded_ids):raise ValueError("A catalogue ID cannot be both locked and excluded")
        if any(not ref.strip() or len(ref)>1000 for ref in self.source_references):raise ValueError("Invalid source reference")
        return self


class CPUReferenceRequest(WireModel):
    storm: Storm
    antecedent_saturation: FiniteFloat = Field(default=.25, ge=0, le=1)


def content_hash(value: dict | WireModel) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    # This identity is minted on the server. Browser retains it, never recreates
    # Python's float serialisation as an independent implementation.
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


CONTRACT_MODELS = (Grid, Storm, SolverConfig, Intervention, Design, PrepareRequest, PlanningRequest, CPUReferenceRequest)
