"""Read USGS NetCDF metadata without reading held-out water-level arrays.

The allowlist intentionally excludes observed extrema and descriptive summaries.
Coordinates and the time axis are metadata; flood levels remain sealed.
"""
import hashlib
from pathlib import Path

import h5py
import numpy as np

GLOBAL_FIELDS = (
    'geospatial_vertical_units', 'geospatial_vertical_reference',
    'time_coverage_resolution', 'time_zone', 'stn_station_number',
    'stn_instrument_id', 'time_coverage_start', 'time_coverage_end',
    'sensor_orifice_elevation_at_deployment_time',
    'sensor_orifice_elevation_at_retrieval_time', 'sensor_orifice_elevation_units',
    'initial_land_surface_elevation', 'final_land_surface_elevation',
    'land_surface_elevation_units',
)
VARIABLE_FIELDS = ('units', 'calendar', 'datum', 'comment', 'standard_name',
                   'scale_factor', 'add_offset', 'ancillary_variables', '_FillValue')
VARIABLES = ('time', 'latitude', 'longitude', 'altitude',
             'water_surface_height_above_reference_datum',
             'unfiltered_water_surface_height_above_reference_datum')


def plain(value):
    if isinstance(value, bytes):
        return value.decode('utf-8')
    if isinstance(value, np.ndarray):
        return plain(value.item()) if value.size == 1 else [plain(x) for x in value]
    if isinstance(value, np.generic):
        return plain(value.item())
    return value


def metadata_only(path: Path) -> dict:
    path = Path(path)
    with h5py.File(path, 'r') as data:
        result = {'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'global_attributes': {k: plain(data.attrs[k]) for k in GLOBAL_FIELDS if k in data.attrs},
                      'variables': {k: {a: plain(data[k].attrs[a]) for a in VARIABLE_FIELDS
                                     if a in data[k].attrs} for k in VARIABLES if k in data},
                      'coordinates': {}, 'observation_values_read': False}
        for name in ('latitude', 'longitude'):
            variable = data[name]
            if variable.shape != ():
                raise ValueError('Expected scalar sensor coordinate')
            value = float(variable[()]) * float(plain(variable.attrs.get('scale_factor', 1)))
            value += float(plain(variable.attrs.get('add_offset', 0)))
            if not np.isfinite(value) or abs(value) > (90 if name == 'latitude' else 180):
                raise ValueError('Invalid sensor coordinate')
            result['coordinates'][name] = value
        tmeta = result['variables']['time']
        if tmeta.get('units') != 'milliseconds since 1970-01-01 00:00:00':
            raise ValueError('Unreviewed sensor time encoding')
        if result['global_attributes'].get('time_zone') not in ('GMT', 'UTC'):
            raise ValueError('Ambiguous NetCDF timezone')
        times = np.asarray(data['time'][:], dtype=float) * tmeta.get('scale_factor', 1)
        times += tmeta.get('add_offset', 0)
        if len(times) < 2 or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
            raise ValueError('Invalid sensor time axis')
        result['time_axis'] = {'count': len(times), 'first_unix_ms': float(times[0]),
                                   'last_unix_ms': float(times[-1]),
                                   'interval_seconds': np.unique(np.diff(times) / 1000).tolist()}
    return result


def require_comparison_ready(review: dict) -> None:
    """A run must not silently convert unresolved metadata into validation."""
    required = ('datum_units_time_verified', 'locations_resolved',
                'sensor_wetness_policy_frozen', 'channel_geometry_supported',
                'independent_boundary_forcing_supported', 'scoring_protocol_frozen')
    missing = [k for k in required if review.get(k) is not True]
    if missing:
        raise ValueError('Comparison preflight incomplete: ' + ', '.join(missing))
