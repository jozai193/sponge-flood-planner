import h5py
import numpy as np
import pytest

from services.reference.sensor_metadata import metadata_only, require_comparison_ready


def fixture(path):
    with h5py.File(path, 'w') as f:
        f.attrs['time_zone'] = 'GMT'
        f.attrs['geospatial_vertical_max'] = 999.123
        f.attrs['summary'] = 'Observed peak must remain hidden'
        f.create_dataset('latitude', data=35.)
        f.create_dataset('longitude', data=-75.)
        t = f.create_dataset('time', data=[0., 30000., 60000.])
        t.attrs['units'] = 'milliseconds since 1970-01-01 00:00:00'
        water = f.create_dataset('water_surface_height_above_reference_datum', data=[999.123]*3)
        water.attrs['max'] = 999.123
        water.attrs['units'] = 'meters'


def test_metadata_does_not_export_observations_or_extrema(tmp_path):
    path = tmp_path/'sensor.nc'; fixture(path)
    r = metadata_only(path)
    assert r['observation_values_read'] is False
    assert '999.123' not in str(r) and 'Observed peak' not in str(r)
    assert r['time_axis']['interval_seconds'] == [30.]


@pytest.mark.parametrize('mutation', ['timezone', 'time_units', 'duplicate_time', 'coordinate'])
def test_rejects_ambiguous_metadata(tmp_path, mutation):
    path = tmp_path/'sensor.nc'; fixture(path)
    with h5py.File(path, 'a') as f:
        if mutation == 'timezone': f.attrs['time_zone'] = 'US/Eastern'
        if mutation == 'time_units': f['time'].attrs['units'] = 'seconds'
        if mutation == 'duplicate_time': f['time'][1] = 0
        if mutation == 'coordinate': f['latitude'][()] = np.nan
    with pytest.raises(ValueError): metadata_only(path)


def test_unresolved_preflight_cannot_be_scored():
    with pytest.raises(ValueError, match='locations_resolved'):
        require_comparison_ready({'datum_units_time_verified': True})


def test_only_explicit_review_passes():
    keys = ('datum_units_time_verified', 'locations_resolved', 'sensor_wetness_policy_frozen',
            'channel_geometry_supported', 'independent_boundary_forcing_supported', 'scoring_protocol_frozen')
    review = dict.fromkeys(keys, True)
    require_comparison_ready(review)
    review['locations_resolved'] = 'pending'
    with pytest.raises(ValueError): require_comparison_ready(review)
