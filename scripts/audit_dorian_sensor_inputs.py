"""Reproducible metadata/terrain audit; never read Dorian flood level arrays."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import rasterio
from pyproj import Transformer

from services.reference.sensor_metadata import metadata_only, require_comparison_ready

ROOT = Path('artifacts/validation/dorian-2019')


def main():
    sites = json.loads((ROOT/'sensor-site-metadata.json').read_text())
    screen = json.loads((ROOT/'candidate-screen.json').read_text())
    d = screen['domain']
    project = Transformer.from_crs(4326, d['projected_crs'], always_xy=True)
    nad_project = Transformer.from_crs(4269, d['projected_crs'], always_xy=True)
    cx, cy = project.transform(d['center_lon'], d['center_lat'])
    rows = []
    for site, fid in zip(sites, (118238, 118294)):
        m = metadata_only(ROOT/'quarantined-observations'/f'{fid}.nc')
        attrs = m['global_attributes']
        if attrs['geospatial_vertical_reference'] != 'NAVD88':
            raise ValueError('Unreviewed datum')
        if m['variables']['water_surface_height_above_reference_datum']['units'] != 'meters':
            raise ValueError('Unreviewed level units')
        if attrs['stn_station_number'].strip() != site['site_no']:
            raise ValueError('Wrong sensor site')
        locations = []
        a = (site['longitude_dd'], site['latitude_dd'])
        b = (m['coordinates']['longitude'], m['coordinates']['latitude'])
        for name, (lon, lat), crs in [('site_catalogue', a, 4269), ('netcdf', b, 4326)]:
            x, y = (nad_project if crs == 4269 else project).transform(lon, lat)
            grid = []
            for n in (64, 128):
                col = int(np.floor((x-cx+1000)/(2000/n)))
                row = int(np.floor((y-cy+1000)/(2000/n)))
                z = np.load(ROOT/f'topobathy-{n}.npy')
                bed = float(z[row, col])
                grid.append({'grid': n, 'row': row, 'col': col, 'bed_m_navd88': bed,
                    'minus_surveyed_local_ground_m': bed-attrs['initial_land_surface_elevation'],
                    'above_sensor_orifice': bed>attrs['sensor_orifice_elevation_at_deployment_time']})
            with rasterio.open(ROOT/'noaa-topobathy-subset.tif') as src:
                # Source declares NAD83 even though the WCS wrapper labels 4326.
                ln, lt = Transformer.from_crs(crs, 4269, always_xy=True).transform(lon, lat)
                rr, cc = src.index(ln, lt)
                arr = src.read(1)
                native = float(arr[rr, cc])
                patch = arr[rr-2:rr+3, cc-2:cc+3]
            locations.append({'source': name, 'lon': lon, 'lat': lat, 'projected_xy': [x,y],
                'native_bed_m_navd88': native, 'native_5x5_range_m': [float(patch.min()),float(patch.max())], 'grids': grid})
        displacement = float(np.linalg.norm(np.subtract(locations[0]['projected_xy'], locations[1]['projected_xy'])))
        row = {'site': site['site_no'], 'metadata': m, 'locations': locations,
                   'catalogue_to_netcdf_distance_m': displacement,
                   'sensor_instrument_id_is_serial_number': True,
                   'filtered_series_present': True, 'per_sample_quality_flags_present': False}
        if fid == 118238:
            fx, fy = project.transform(-75.57425, 35.43493)
            row.update(location_resolved=False,
                field_form_coordinates=[-75.57425,35.43493],
                field_form_to_catalogue_distance_m=float(np.linalg.norm(np.subtract([fx,fy],locations[0]['projected_xy']))),
                reason='CSV and NetCDF agree approximately, but site catalogue differs and both field forms name coordinates far outside the domain. Serial number 997240 agrees. No location chosen to improve a score.')
        else:
            row.update(location_resolved=True,
                field_form_coordinates=[-75.688823,35.218333],
                surveyed_ground_form_m=-.486*.3048,
                surveyed_orifice_form_m=1.451*.3048,
                reason='Catalogue, field forms and NetCDF agree to sub-metre precision. Surveyed local ground and native/grid terrain do not agree; point survey alone does not define channel bathymetry.')
        rows.append(row)
    checks = {'datum_units_time_verified': True,
                  'locations_resolved': all(r['location_resolved'] for r in rows),
                  'sensor_wetness_policy_frozen': False, 'channel_geometry_supported': False,
                  'independent_boundary_forcing_supported': False, 'scoring_protocol_frozen': False}
    try:
        require_comparison_ready(checks)
        raise AssertionError('Unresolved comparison should not pass')
    except ValueError as error:
        gate_message = str(error)
    report = {'status': 'preflight_failed_no_accuracy_run', 'checks': checks, 'gate_message': gate_message,
        'observation_level_arrays_read': False, 'netcdf_files_cached': True, 'production_enabled': False,
        'general_flood_accuracy_validated': False, 'sites': rows,
        'time_decision': 'Use reviewed NetCDF epoch milliseconds in GMT/UTC; do not apply the CSV US/Eastern label to these values.',
        'variable_decision': 'Source includes processed storm-tide and unfiltered arrays. Filename alone cannot select the intended quantity. Declare averaging and wetness rules before opening arrays.',
        'geometry_decision': 'Do not lower an isolated sensor cell to its survey elevation or move it to a wetter cell. Obtain a spatially supported channel/bridge representation.',
        'boundary_decision': 'NOAA 8654467 is an independent nearby sound-side stage input. The 2 km barrier-island box has sound and ocean openings; one gauge does not establish separate ocean forcing or a wind-driven sound gradient.',
        'wave_candidate_decision': 'Incoming-wave characteristic boundary remains unsuitable for total observed gauge forcing; no production adoption.',
        'next_actions': ['Resolve ferry coordinates from an independent georeferenced deployment/survey record.',
                      'Obtain creek bathymetry/bridge opening geometry sufficient to preserve conveyance.',
                      'Specify separate sound/ocean forcing from independent data or a documented regional hindcast.',
                      'Freeze time window, processing, wetness support and metrics, then run both solvers before revealing targets.']}
    files = ['candidate-screen.json','sensor-site-metadata.json','sensor-datafile-metadata.json',
             'noaa-topobathy-subset.tif','topobathy-64.npy','topobathy-128.npy',
             'deployment-117260.pdf','deployment-118277.pdf','recovery-118149.pdf','recovery-118279.pdf',
             'sensor-header-118237.txt','sensor-header-118292.txt']
    report['source_sha256'] = {str(ROOT/f):hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
    for name in ('services/reference/sensor_metadata.py','scripts/audit_dorian_sensor_inputs.py'):
        report['source_sha256'][name] = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    (ROOT/'sensor-input-audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'status': report['status'],'sites': [{k:r[k] for k in ('site','catalogue_to_netcdf_distance_m','locations')} for r in rows]},indent=2))


if __name__ == '__main__':
    main()
