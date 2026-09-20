"""Canonical scenario envelope. Validation is not permission to claim site accuracy."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator


class StrictWire(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class Components(StrictWire):
    rainfall: bool
    external: bool
    coastal: bool


class Interval(StrictWire):
    start_s: FiniteFloat = Field(ge=0)
    end_s: FiniteFloat = Field(gt=0)
    rate_m_s: FiniteFloat = Field(ge=0, le=.001)


class ScenarioStorm(StrictWire):
    duration: FiniteFloat = Field(gt=0)
    recession: FiniteFloat = Field(ge=0)
    depth: FiniteFloat = Field(ge=0)
    intervals: list[Interval] | None = Field(default=None, min_length=1, max_length=10000)


class Inflow(StrictWire):
    cell: int = Field(ge=0)
    flowM3S: FiniteFloat = Field(ge=0)
    startS: FiniteFloat = Field(ge=0)
    endS: FiniteFloat = Field(gt=0)
    source: str = Field(min_length=1, pattern=r'\S')


class Outlet(StrictWire):
    cell: int = Field(ge=0)
    crestDepthM: FiniteFloat = Field(ge=0)
    ratePerS: FiniteFloat = Field(ge=0)
    maxFlowM3S: FiniteFloat = Field(ge=0)
    tailwaterElevationM: FiniteFloat | None = None
    source: str = Field(min_length=1, pattern=r'\S')


class Level(StrictWire):
    timeS: FiniteFloat = Field(ge=0)
    elevationM: FiniteFloat


class Coast(StrictWire):
    edge: Literal['west', 'east', 'south', 'north']
    cells: list[int] = Field(min_length=1, max_length=2048)
    levels: list[Level] = Field(min_length=1, max_length=10000)
    source: str = Field(min_length=1, pattern=r'\S')
    datum: str = Field(min_length=1, pattern=r'\S')
    segment_ids: list[str] = Field(default_factory=list, max_length=2048)
    source_kind: Literal['measured','modelled','assumed'] = 'assumed'
    source_epoch: str = 'unknown'
    vertical_transform: str = 'unverified'
    coverage_start_s: FiniteFloat | None = Field(default=None, ge=0)
    coverage_end_s: FiniteFloat | None = Field(default=None, ge=0)
    bathymetry_status: Literal['verified','missing','not_required'] = 'missing'
    channel_support_status: Literal['verified','missing','not_required'] = 'missing'


class ScenarioForcing(StrictWire):
    version: Literal[2]
    components: Components
    storm: ScenarioStorm
    coastal: Coast | None = None
    inflows: list[Inflow] = Field(max_length=4194304)
    outlets: list[Outlet] = Field(max_length=4194304)


class ScenarioDomain(StrictWire):
    nx: int = Field(ge=4, le=2048)
    ny: int = Field(ge=4, le=2048)
    dx_m: FiniteFloat = Field(gt=0)
    dy_m: FiniteFloat = Field(gt=0)
    horizontal_crs: str = Field(min_length=1)
    vertical_datum: str = Field(min_length=1)
    elevation_origin_m: FiniteFloat | None = None
    # Legacy saved/local fixtures may use opaque IDs; this is provenance, not
    # the executable digest or an access capability. API bundle access is separate.
    bundle_id: str | None = Field(default=None, min_length=1, max_length=200)


class ScenarioSpecV2(StrictWire):
    version: Literal[2]
    engine: str = Field(min_length=1, max_length=100)
    domain: ScenarioDomain
    forcing: ScenarioForcing
    required_capabilities: list[str] = Field(max_length=32)
    execution_input_hash: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')

    @model_validator(mode='after')
    def physical_consistency(self):
        f, d = self.forcing, self.domain
        c, s = f.components, f.storm
        if not any((c.rainfall, c.external, c.coastal)):
            raise ValueError('Enable at least one flood source')
        if c.coastal != (f.coastal is not None) or c.external != bool(f.inflows):
            raise ValueError('Enabled components must match supplied sources')
        if not c.rainfall and (s.depth != 0 or s.intervals is not None):
            raise ValueError('Disabled rainfall contains forcing')
        end, depth = 0., 0.
        for i in s.intervals or []:
            if i.start_s < end or i.end_s <= i.start_s or i.end_s > s.duration:
                raise ValueError('Invalid rainfall interval order or duration')
            end = i.end_s
            depth += (i.end_s-i.start_s)*i.rate_m_s
        if s.intervals is not None and abs(depth-s.depth) > max(1e-9,s.depth*1e-4):
            raise ValueError('Rainfall integral does not match event depth')
        n, finish = d.nx*d.ny, s.duration+s.recession
        for rows in (f.inflows, f.outlets):
            cells = [i.cell for i in rows]
            if any(i >= n for i in cells) or len(cells) != len(set(cells)):
                raise ValueError('Invalid or duplicate source cells')
        for i in f.inflows:
            if i.endS <= i.startS or i.endS > finish:
                raise ValueError('Inflow exceeds simulation window')
        if f.coastal:
            b = f.coastal
            if len(b.cells) != len(set(b.cells)):
                raise ValueError('Duplicate coastal cells')
            for i in b.cells:
                x,y = i%d.nx,i//d.nx
                edge = {'west':x==0,'east':x==d.nx-1,'south':y==0,'north':y==d.ny-1}[b.edge]
                if not 0 <= i < n or not edge:
                    raise ValueError('Invalid coastal boundary cell')
            if b.levels[0].timeS != 0 or any(a.timeS >= z.timeS for a,z in zip(b.levels,b.levels[1:])):
                raise ValueError('Invalid coastal level series')
            if b.levels[-1].timeS > finish:
                raise ValueError('Coastal series exceeds simulation window')
            if set(b.cells).intersection(i.cell for i in f.inflows):
                raise ValueError('External inflow overlaps coastal boundary')
        return self
