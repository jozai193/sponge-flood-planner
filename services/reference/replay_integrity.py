"""Validate physical replay outputs before scoring observations."""
import numpy as np


def validate_replay(frames, shape, solid, duration_s, expected_frames=121,
                    mass_tolerance=.001, depth_tolerance=1e-6, cell_area_m2=None):
    if not np.isfinite(duration_s) or duration_s<=0:raise ValueError('Invalid duration')
    if len(frames)!=expected_frames:raise ValueError('Incomplete replay frame count')
    mask=np.asarray(solid)
    if mask.shape!=tuple(shape) or not np.isin(mask,[0,1]).all():raise ValueError('Invalid solid mask')
    if not np.isfinite(mass_tolerance) or mass_tolerance<=0:raise ValueError('Invalid mass tolerance')
    if cell_area_m2 is not None and (not np.isfinite(cell_area_m2) or cell_area_m2<=0):raise ValueError('Invalid cell area')
    times=np.array([f['time_s'] for f in frames],dtype=float)
    if not np.isfinite(times).all() or abs(times[0])>1e-7 or abs(times[-1]-duration_s)>1e-5 or np.any(np.diff(times)<=0):
        raise ValueError('Replay timestamps must span event in increasing order')
    previous_peak=None;maximum_residual=0.
    ledger_keys=('initial_m3','rain_m3','inflow_m3','stored_m3','outflow_m3','deep_percolation_m3','residual_m3','relative_residual')
    for frame in frames:
        depth=np.asarray(frame['depth'],dtype=float).reshape(shape)
        peak=np.asarray(frame['maxDepth'],dtype=float).reshape(shape)
        if not np.isfinite(depth).all() or not np.isfinite(peak).all() or np.any(depth<0) or np.any(peak<0):
            raise ValueError('Nonfinite or negative replay depth')
        if np.any(peak+depth_tolerance<depth):raise ValueError('Peak history below current depth')
        if previous_peak is not None and np.any(peak+depth_tolerance<previous_peak):
            raise ValueError('Peak history decreases')
        if np.any(depth[mask==1]>depth_tolerance) or np.any(peak[mask==1]>depth_tolerance):
            raise ValueError('Replay water inside solid cells')
        previous_peak=peak
        ledger=frame['ledger']
        if any(k not in ledger or not np.isfinite(ledger[k]) for k in ledger_keys):
            raise ValueError('Missing or nonfinite water ledger')
        if any(ledger[k]<0 for k in ledger_keys if k!='residual_m3'):
            raise ValueError('Negative water accounting')
        if cell_area_m2 is not None:
            for k in ('surface_m3','subsurface_m3'):
                if k not in ledger or not np.isfinite(ledger[k]) or ledger[k]<0:
                    raise ValueError('Missing or invalid stored water partition')
            measured_surface=float(depth[mask==0].sum()*cell_area_m2)
            if not np.isclose(measured_surface,ledger['surface_m3'],rtol=2e-6,atol=1e-5):
                raise ValueError('Saved depths disagree with surface water ledger')
            if not np.isclose(ledger['stored_m3'],ledger['surface_m3']+ledger['subsurface_m3'],rtol=2e-6,atol=1e-5):
                raise ValueError('Stored water partition inconsistent')
        supplied=ledger['initial_m3']+ledger['rain_m3']+ledger['inflow_m3']
        residual=supplied-ledger['stored_m3']-ledger['outflow_m3']-ledger['deep_percolation_m3']
        if not np.isclose(residual,ledger['residual_m3'],rtol=1e-6,atol=1e-6):
            raise ValueError('Inconsistent signed water ledger')
        relative=abs(residual)/max(supplied,1.)
        if not np.isclose(relative,ledger['relative_residual'],rtol=1e-6,atol=1e-10):
            raise ValueError('Inconsistent relative water ledger')
        maximum_residual=max(maximum_residual,relative)
    return {'frames': len(frames),'duration_s': float(times[-1]),
        'max_recorded_relative_mass_residual': maximum_residual,
        'mass_gate_passed': maximum_residual<=mass_tolerance,
        'replay_structure_passed': True,
        'depth_volume_crosscheck_passed': True if cell_area_m2 is not None else None,
        'limitation': 'Checks saved outputs and ledger consistency, not every unsaved solver step or real-world accuracy.'}
