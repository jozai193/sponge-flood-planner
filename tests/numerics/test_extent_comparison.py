import numpy as np
import pytest
from shapely.geometry import box

from services.reference.extent_comparison import mapped_flood_coverage


def test_fractional_cells_preserve_missed_and_unresolved_area():
    g={'nx': 2,'ny': 2,'dx_m': 2,'dy_m': 3,'origin_x_m': 0,'origin_y_m': 0,'row_direction': 'north'}
    peak=np.array([[.2,0],[.2,.2]])
    solid=np.array([[0,0],[1,0]])
    result=mapped_flood_coverage(g,peak,solid,box(1,0,3,6))
    assert result['mapped_area_m2']==12
    assert result['building_unresolved_area_m2']==3
    assert result['predicted_dry_mapped_area_m2']==3
    assert result['predicted_wet_mapped_area_m2']==6
    assert result['mapped_wet_fraction']==pytest.approx(2/3)
    assert 'precision' not in result


def test_initial_water_is_disclosed_not_counted_as_new_inundation():
    g={'nx': 2,'ny': 1,'dx_m': 1,'dy_m': 1,'origin_x_m': 0,'origin_y_m': 0,'row_direction': 'north'}
    result=mapped_flood_coverage(g,[[2,.2]],[[0,0]],box(0,0,2,1),[[2,0]])
    assert result['model_initially_wet_mapped_area_m2']==1
    assert result['newly_wet_mapped_area_m2']==1
    assert result['initially_dry_nonbuilding_mapped_area_m2']==1
