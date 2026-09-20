import json

import numpy as np
import pytest

from services.api.contracts import CPUReferenceRequest
from services.reference.bundle_runner import run_bundle_reference
from services.reference.process_runner import run_reference_bounded


def fixture(tmp_path,n=4):
    folder=tmp_path/'bundle';folder.mkdir();grid={'nx': n,'ny': n,'dx_m': 1.,'dy_m': 1.,'crs': 'LOCAL_METRES','origin_x_m': 0.,'origin_y_m': 0.,'elevation_origin_m': 0.,'row_direction': 'north','vertical_datum': 'fixture'}
    (folder/'manifest.json').write_text(json.dumps({'bundle_id': 'b','grid': grid}))
    for name,array in {'z':np.zeros(n*n,'f4'),'solid':np.zeros(n*n,'u1'),'roughness':np.full(n*n,.03,'f4'),'infiltration':np.zeros(n*n,'f4'),'soil_capacity':np.zeros(n*n,'f4'),'rain_weights':np.ones(n*n,'f4')}.items():array.tofile(folder/f'{name}.bin')
    return folder

def test_cpu_reference_fallback_runs_full_storm_and_recession(tmp_path):
    request=CPUReferenceRequest(storm={'name': 'fixture','duration_s': 2.,'recession_s': 2.,'depth_m': .002,'intervals': [{'start_s': 0.,'end_s': 2.,'rate_m_s': .001}]})
    result=run_bundle_reference(fixture(tmp_path),request);frame=result['frame']
    assert result['engine']=='cpu-hll-float64' and frame['time_s']==4 and len(frame['depth'])==16
    assert frame['ledger']['rain_m3']==pytest.approx(.032) and frame['ledger']['relative_residual']<1e-9

def test_cpu_reference_fallback_rejects_oversized_grid(tmp_path):
    request=CPUReferenceRequest(storm={'name': 'fixture','duration_s': 1.,'recession_s': 0.,'depth_m': 0.,'intervals': [{'start_s': 0.,'end_s': 1.,'rate_m_s': 0.}]})
    with pytest.raises(ValueError,match='128'):run_bundle_reference(fixture(tmp_path,129),request)


def test_cpu_reference_runs_in_bounded_child_process(tmp_path):
    request=CPUReferenceRequest(storm={'name': 'fixture','duration_s': 2.,'recession_s': 0.,'depth_m': .002,'intervals': [{'start_s': 0.,'end_s': 2.,'rate_m_s': .001}]})
    result=run_reference_bounded(fixture(tmp_path),request)
    assert result['engine']=='cpu-hll-float64'
    assert result['frame']['time_s']==2
