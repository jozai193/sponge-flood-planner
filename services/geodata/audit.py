"""Provider-independent evidence audit. Coverage is not completeness or calibration."""
import hashlib
import json
from pathlib import Path

import numpy as np
from shapely.geometry import shape

from services.geodata.source_dates import source_dates


def audit_bundle(folder: Path) -> dict:
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    grid = manifest['grid']
    quality = manifest.get('quality', {})
    checks = []
    def add(key, title, status, detail):
        checks.append({'key': key, 'title': title, 'status': status, 'detail': detail})

    # Only canonical filenames are read, never paths supplied by a manifest.
    arrays = {}
    errors = []
    for name, dtype in [('z', '<f4'), ('solid', 'u1')]:
        artifact = next((a for a in manifest.get('artifacts', []) if a['name'] == name), None)
        path = folder / f'{name}.bin'
        if not path.exists():
            errors.append(f'{name}: missing artifact')
            continue
        raw = path.read_bytes()
        expected = grid['nx'] * grid['ny'] * np.dtype(dtype).itemsize
        if len(raw) != expected or not artifact or hashlib.sha256(raw).hexdigest() != artifact.get('sha256'):
            errors.append(f'{name}: size or checksum mismatch')
            continue
        array = np.frombuffer(raw, dtype=dtype)
        if not np.isfinite(array).all():
            errors.append(f'{name}: non-finite values')
            continue
        arrays[name] = array
    add('integrity', 'Terrain and obstacle integrity', 'failed' if errors else 'checked',
        '; '.join(errors) if errors else 'Array sizes, SHA-256 checksums and finite values checked.')
    native = quality.get('native_resolution_m')
    add('resolution', 'Terrain resolution', 'reported' if native else 'unknown',
        f"Simulation cells: {grid['dx_m']:.2f} × {grid['dy_m']:.2f} m. " +
        (f'Provider-reported native resolution: {native} m; resampling adds no detail.' if native else
         'Native source resolution unknown; smaller simulation cells do not establish finer terrain accuracy.'))
    dates=source_dates(manifest.get('sources',[]))
    dated=sum(bool(s['observation_dates']) for s in dates)
    add('source_dates','Data dates','reported' if dates and dated==len(dates) else 'incomplete',
        f'{dated} of {len(dates)} distinct source records state an observation or acquisition date. '
        'A publication, product release or recent download is not the survey date. '
        'Annual land-cover products describe a classification period; individual capture dates can differ. '
        'Source age and changes on the ground require review before using this location for planning.')
    terrain=None
    if 'z' in arrays and 'solid' in arrays:
        from services.geodata.topography import terrain_metrics
        terrain=terrain_metrics(arrays['z'].reshape(grid['ny'],grid['nx']),grid['dx_m'],grid['dy_m'],arrays['solid'].reshape(grid['ny'],grid['nx']))
        origin=grid.get('elevation_origin_m',0)
        add('topography','High and low ground','computed',
            f"Source elevations: {terrain['min_elevation_m']+origin:.2f} to {terrain['max_elevation_m']+origin:.2f} m; relief {terrain['relief_m']:.2f} m. "
            f"Mapped depression storage to edge spill levels: {terrain['depression_storage_m3']:.1f} m3; deepest depression {terrain['deepest_depression_m']:.2f} m. "
            f"Building-enclosed ground without an edge path: {terrain['unresolved_enclosed_area_m2']:.1f} m2, excluded from that storage estimate. "
            'Diagnostic only: domain edges are not verified outlets, buildings are blocking cells, and depressions are preserved in the simulation.')
        add('vertical_reference','Elevation reference','reported',
            f"Datum: {grid.get('vertical_datum','unknown')}. Local numerical zero offset: {origin:.2f} m. "
            'Subtracting this common offset preserves all relative heights. Curbs, walls, ramps and raised plots require sufficiently detailed surveyed ground data; display detail supplies no elevation evidence.')
    if quality.get('terrain_selection_note'):
        add('terrain_selection','Terrain provider selection','reported',quality['terrain_selection_note'])
    buildings = manifest.get('buildings', [])
    occupied = float(np.count_nonzero(arrays['solid']) / arrays['solid'].size * 100) if 'solid' in arrays else None
    add('buildings', 'Building coverage', 'unverified',
        f'{len(buildings)} mapped footprints; ' +
        (f'{occupied:.1f}% of grid cells occupied. ' if occupied is not None else '') +
        'Completeness is unknown without an independent reference survey. Empty map areas are not confirmed open land.')
    alignment_errors=[]
    required_grid=('crs','origin_x_m','origin_y_m','dx_m','dy_m','nx','ny','row_direction','vertical_datum','elevation_origin_m')
    if not all(key in grid for key in required_grid):alignment_errors.append('grid reference metadata is incomplete')
    extent=manifest.get('extent_m')
    if not isinstance(extent,(int,float)) or not np.isfinite(extent) or extent<=0:alignment_errors.append('model extent is invalid')
    if not alignment_errors:
        half=extent/2;solid=arrays.get('solid')
        for building in buildings:
            try:
                geometry=shape(building['geometry']);bounds=geometry.bounds
                if geometry.is_empty or not geometry.is_valid or min(bounds)<-half-1e-6 or max(bounds)>half+1e-6:
                    raise ValueError
                if not np.isfinite(building['base_elevation_m']):raise ValueError
                for cell in building.get('exterior_cells',[]):
                    if not isinstance(cell,int) or not 0<=cell<grid['nx']*grid['ny'] or (solid is not None and solid[cell]):raise ValueError
            except (KeyError,TypeError,ValueError):alignment_errors.append(f"building {building.get('id','unknown')} is not aligned to the canonical local grid");break
        for candidate in manifest.get('candidates',[]):
            try:
                col=int(np.floor((candidate['x_m']+half)/grid['dx_m']));row=int(np.floor((candidate['y_m']+half)/grid['dy_m']))
                center=row*grid['nx']+col
                if not (0<=col<grid['nx'] and 0<=row<grid['ny']) or center not in candidate['cells'] or any(not isinstance(cell,int) or not 0<=cell<grid['nx']*grid['ny'] or (solid is not None and solid[cell]) for cell in candidate['cells']):raise ValueError
            except (KeyError,TypeError,ValueError):alignment_errors.append(f"candidate {candidate.get('id','unknown')} does not resolve to its canonical grid cells");break
    add('alignment','Horizontal and vertical alignment','failed' if alignment_errors else 'checked',
        '; '.join(alignment_errors) if alignment_errors else f"Terrain cells, local-metre building geometry and candidate picks share {grid['crs']}; row direction {grid['row_direction']}. Building and display-water elevations use the terrain local zero offset {grid['elevation_origin_m']:.2f} m. This internal alignment does not resolve the external datum claim ({grid['vertical_datum']}).")
    sourced = sum(str(b.get('height_source','')).startswith('provider') for b in buildings)
    floor_estimated = sum(str(b.get('height_source','')).startswith('estimated from mapped floors') for b in buildings)
    declared_verified = sum(b.get('height_source') == 'verified' for b in buildings)
    assumed = len(buildings)-sourced-floor_estimated-declared_verified
    add('heights', 'Building heights and exposure', 'unverified',
        f'{sourced} source-reported heights; {floor_estimated} heights estimated from floor counts; '
        f'{assumed} assumed or unknown heights; {declared_verified} records labelled verified by their input source. '
        'These labels are provenance, not independent verification. First-floor elevations and valuations require independent evidence.')
    add('appearance', 'Real-world building appearance', 'not_replicated',
        'This scene extrudes mapped footprints. Roof forms, facade materials and windows are illustrative; '
        'no textured photogrammetric or surveyed building models are attached. Satellite imagery is a ground image, '
        'not a source of measured building heights. More footprints do not establish an exact city replica.')
    for key, title, detail in [
        ('materials', 'Soils and greenery', 'WorldCover classes drive exploratory, uncalibrated material presets.' if quality.get('materials')=='source_classified_exploratory_presets' else 'Uniform, uncalibrated infiltration and roughness. Imagery and display greenery do not classify hydraulic materials.'),
        ('drainage', 'Drainage network', 'No verified coupled pipe network in this bundle. Scenario outlets are separate user inputs; they do not establish network capacity or surcharge.'),
        ('boundary', 'Contributing catchment', 'The selected map square is not a verified catchment. Upstream inflow and downstream water levels need evidence.'),
        ('observation_validation', 'Observed flood validation', 'No observed flood comparison is attached. Numerical conservation does not establish local predictive accuracy.'),
        ('parcels', 'Intervention eligibility', 'Open-ground candidates have no verified ownership, utilities or construction eligibility.'),
    ]:
        add(key, title, 'unverified', detail)
    return {'schema_version': 'sponge.audit.v1', 'bundle_id': manifest['bundle_id'],
                'scope': 'Prepared bundle only; excludes active scenario edits and visual imagery',
                'terrain': terrain, 'checks': checks, 'sources': manifest.get('sources', []),'source_dates': dates,
                'quantitative_use': 'not_validated', 'location': manifest.get('location')}
