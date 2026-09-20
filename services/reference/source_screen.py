"""Conservative admission checks for external flood evidence.

Metadata screening is not scientific validation. Unknown fields never grant
permission to score, and tile footprints never establish valid image pixels.
"""
import re
from datetime import UTC, datetime

from shapely.geometry import shape


def extent_score_admission(source):
    """Require an explicitly reviewed observed wet/dry reference for area scores."""
    reasons = []
    if source.get('evidence_kind') != 'observed_wet_dry_extent':
        reasons.append('Source is not a reviewed observed wet/dry extent')
    for field in ('independent_of_model', 'survey_coverage_verified',
                  'dry_areas_observed', 'permanent_water_excluded',
                  'event_time_aligned', 'georeferencing_reviewed'):
        if source.get(field) is not True:
            reasons.append(field + ' is unverified')
    return {'eligible_for_precision_iou': not reasons, 'reasons': reasons}


def tile_date_review(item):
    """Keep STAC timestamps and filename date hints separate; do not repair either."""
    timestamp = item.get('properties', {}).get('datetime')
    match = re.match(r'^(\d{8})', item.get('id', ''))
    hint = None
    if match:
        try:
            hint = datetime.strptime(match[1], '%Y%m%d').replace(tzinfo=UTC).date().isoformat()
        except ValueError:
            pass
    try:
        declared = datetime.fromisoformat(timestamp).date().isoformat()
    except (AttributeError, ValueError, TypeError):
        declared = None
    conflict = bool(hint and declared and hint != declared)
    return {'stac_datetime': timestamp, 'filename_date_hint': hint,
            'date_conflict': conflict, 'capture_time_verified': False}


def intersecting_tiles(items, domain):
    """Use actual catalog geometries, not a collection bounding envelope."""
    if domain.is_empty or not domain.is_valid:
        raise ValueError('Valid nonempty domain required')
    selected = []
    for item in items:
        geom = shape(item['geometry'])
        if geom.is_empty or not geom.is_valid:
            raise ValueError('Invalid source footprint: ' + item.get('id', 'unknown'))
        if geom.intersection(domain).area > 0:
            selected.append(item)
    return selected
