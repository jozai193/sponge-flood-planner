import pytest
from shapely.geometry import Polygon, box, mapping

from services.reference.source_screen import extent_score_admission, intersecting_tiles, tile_date_review


def valid_reference():
    return {'evidence_kind': 'observed_wet_dry_extent', 'independent_of_model': True,
                'survey_coverage_verified': True, 'dry_areas_observed': True,
                'permanent_water_excluded': True, 'event_time_aligned': True,
                'georeferencing_reviewed': True}


@pytest.mark.parametrize('kind', ['post_event_imagery', 'model_output', 'hwm_dem_derived', 'hazard_forecast'])
def test_non_observed_products_cannot_be_promoted_by_other_metadata(kind):
    assert not extent_score_admission({**valid_reference(), 'evidence_kind': kind})['eligible_for_precision_iou']


def test_unknown_dry_coverage_prevents_false_positive_score():
    source = valid_reference()
    assert extent_score_admission(source)['eligible_for_precision_iou']
    source.pop('dry_areas_observed')
    assert not extent_score_admission(source)['eligible_for_precision_iou']
    source['dry_areas_observed'] = 'true'
    assert not extent_score_admission(source)['eligible_for_precision_iou']


def test_conflicting_dates_are_retained_without_assuming_filename_is_truth():
    result = tile_date_review({'id': '20190907a_tile', 'properties': {'datetime': '2019-09-04T00:00:00Z'}})
    assert result['date_conflict']
    assert result['filename_date_hint'] == '2019-09-07'
    assert result['stac_datetime'] == '2019-09-04T00:00:00Z'
    assert not result['capture_time_verified']


def test_catalog_holes_and_touching_edges_do_not_count_as_coverage():
    ring = Polygon([(0,0),(4,0),(4,4),(0,4)], holes=[[(1,1),(1,3),(3,3),(3,1)]])
    items = [{'id': 'hole', 'geometry': mapping(ring)}, {'id': 'touch', 'geometry': mapping(box(2,1,4,2))}]
    assert intersecting_tiles(items, box(1,1,2,2)) == []
