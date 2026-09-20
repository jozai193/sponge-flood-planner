"""Cache public metadata and prepare a zero-account, metadata-only GIS review.

Run with --fetch for missing metadata; subsequent runs reproduce from the cache.
No imagery pixels, paid APIs, model changes or hidden HWM elevations are accessed.
"""
import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from html import escape
from pathlib import Path

import httpx
from pyproj import Transformer
from shapely.geometry import Point, box, mapping, shape
from shapely.ops import transform, unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.reference.source_screen import extent_score_admission, intersecting_tiles, tile_date_review

ROOT = Path('artifacts/validation/free-data-workflow')
BASE = 'https://coastalimagery.blob.core.windows.net/digitalcoast/HurricaneDorian_2019_8891/'
SOURCES = {
    'dorian-stac-items.json': BASE + 'stac/noaa_imagery_item_collection_m8891.json',
    'arcgis-dorian-item.json': 'https://www.arcgis.com/sharing/rest/content/items/0025fc18e85841fba8a85fa4d4c6c83b?f=json',
    'noaa-dorian-metadata.xml': BASE + '2019_NGS_NaturalColorImagery_m8891_met.xml',
}


def load_sources(fetch):
    records = []
    for name, url in SOURCES.items():
        path = ROOT / name
        if not path.exists():
            if not fetch:
                raise RuntimeError('Missing metadata; run with --fetch: ' + name)
            data = bytearray()
            with httpx.stream('GET', url, timeout=60, follow_redirects=True) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 50_000_000:
                        raise ValueError('Metadata exceeds 50 MB limit')
            if name.endswith('.json'):
                parsed = json.loads(data)
                if 'error' in parsed:
                    raise ValueError('Remote service returned an error')
            path.write_bytes(data)
        records.append({'file': name, 'url': url, 'bytes': path.stat().st_size,
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'cached_file_modified_utc': datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()})
    return records


def write_json(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    provenance = load_sources(args.fetch)
    # This explicitly redacted metadata fixture has no observed elevations.
    screen_path = Path('artifacts/validation/dorian-2019/candidate-screen.json')
    screen = json.loads(screen_path.read_text())
    d = screen['domain']
    forward = Transformer.from_crs(4326, d['projected_crs'], always_xy=True)
    inverse = Transformer.from_crs(d['projected_crs'], 4326, always_xy=True)
    cx, cy = forward.transform(d['center_lon'], d['center_lat'])
    domain_m = box(cx-1000, cy-1000, cx+1000, cy+1000)
    domain = transform(inverse.transform, domain_m)
    items = json.loads((ROOT/'dorian-stac-items.json').read_text())['features']
    selected = intersecting_tiles(items, domain)
    arcgis = json.loads((ROOT/'arcgis-dorian-item.json').read_text())
    stated = box(*arcgis['extent'][0], *arcgis['extent'][1])
    footprints = unary_union([shape(t['geometry']) for t in selected])
    covered = transform(forward.transform, footprints).intersection(domain_m).area
    tiles = []
    tile_features = []
    for item in selected:
        record = dict(id=item['id'], **tile_date_review(item),
                      stac_license=item['properties'].get('license'),
                      asset_urls=[v['href'] for v in item.get('assets', {}).values()])
        tiles.append(record)
        tile_features.append({'type': 'Feature', 'geometry': item['geometry'], 'properties': {
            'tile_id': record['id'], 'stac_datetime': record['stac_datetime'],
            'filename_date_hint': record['filename_date_hint'], 'date_conflict': record['date_conflict'],
            'asset_url': record['asset_urls'][0] if record['asset_urls'] else '',
            'pixel_coverage_verified': False}})
    marks = []
    for mark in screen['marks']:
        to_wgs = Transformer.from_crs({2:4269,3:4267,4:4326}[mark['hdatum_id']],4326,always_xy=True)
        lon,lat = to_wgs.transform(mark['longitude_dd'],mark['latitude_dd'])
        point = Point(lon,lat)
        marks.append({'type': 'Feature', 'geometry': mapping(point), 'properties': {
            'hwm_id': mark['hwm_id'], 'tile_ids': ', '.join(t['id'] for t in selected if shape(t['geometry']).covers(point)),
            'reference_role': 'location_only_no_observed_height', 'setting_resolved_by_this_audit': False}})
    def geojson(name, features):
        write_json(name, {'type': 'FeatureCollection', 'features': features})
    geojson('dorian-tile-footprints.geojson', tile_features)
    geojson('dorian-reference-locations.geojson', marks)
    geojson('dorian-domain.geojson', [{'type': 'Feature','geometry': mapping(domain),'properties': {'extent_m':2000}}])
    candidates = [
        {'id': 'noaa-dorian-imagery', 'evidence_kind': 'post_event_imagery',
             'use': 'Inspect event-era building context after reviewing pixels, georeferencing and acquisition time.',
             'source_url': 'https://www.fisheries.noaa.gov/inport/item/57856/full-list',
             'access': 'Public bulk metadata and image URLs; no account used.',
             'license_review': 'NOAA InPort declares CC0. STAC says NLPL; retain conflict and cite primary NOAA metadata.'},
        {'id': 'nyc-sandy-extent', 'evidence_kind': 'hwm_dem_derived',
             'use': 'Existing mapped-wet coverage diagnostic; shares HWM/DEM evidence and has no surveyed dry coverage.',
             'source_url': 'https://data.cityofnewyork.us/Environment/Sandy-Inundation-Zone/uyj8-7rv5'},
        {'id': 'usgs-matthew-overwash', 'evidence_kind': 'sediment_deposit_extent',
             'use': 'Coastal-change context; deposited sand is not a complete wet/dry flood boundary.',
             'source_url': 'https://coastal.er.usgs.gov/data-release/doi-P9BW6CG6/'},
        {'id': 'fastflood', 'evidence_kind': 'model_output',
             'use': 'Optional manual comparator only after matching inputs; not part of automated regression.',
             'source_url': 'https://fastflood.org/products',
             'free_tier': '10 simulations listed, reset period unspecified; personal use; CLI excluded.'},
    ]
    for source in candidates:
        source['area_score_admission'] = extent_score_admission(source)
    report = {'audited_at': datetime.now(UTC).isoformat(),
                  'status': 'metadata_review_complete_no_new_accuracy_claim',
                  'software_cost': 0, 'accounts_created': 0, 'imagery_pixels_downloaded': False,
                  'hidden_hwm_elevations_exposed': False, 'production_model_changed': False,
                  'source_files': provenance,
                  'candidate_screen_sha256': hashlib.sha256(screen_path.read_bytes()).hexdigest(),
                  'arcgis': {'id': arcgis['id'], 'access': arcgis['access'], 'owner': arcgis['owner'],
                              'stated_extent_intersects_domain': stated.intersects(domain),
                              'interpretation': 'Discovery listing extent disagrees with primary tile catalog; not authoritative pixel coverage.'},
                  'total_catalog_tiles': len(items), 'intersecting_tile_count': len(tiles),
                  'catalog_footprint_domain_fraction': covered/domain_m.area,
                  'valid_pixel_coverage_verified': False, 'tiles': tiles, 'sources': candidates,
                  'next_steps': ['Review the two site locations against event-era imagery; retain ambiguous mark as unscored.',
                              'Resolve per-tile capture times before any time-specific flood comparison.',
                              'Resolve sound/ocean forcing before freezing Dorian protocol.',
                              'Continue seeking independently observed wet AND dry coverage; no eligible area reference found in this screen.']}
    write_json('source-audit.json', report)
    rows = ''.join('<tr><td>'+escape(t['id'])+'</td><td>'+escape(str(t['stac_datetime']))+'</td><td>'+escape(str(t['filename_date_hint']))+'</td><td>'+str(t['date_conflict'])+'</td></tr>' for t in tiles)
    sources_html = ''.join(f'<li><a href="{escape(s["source_url"],quote=True)}">{escape(s["id"])}</a>: {escape(s["use"])} Area scoring admitted: <b>no</b>.</li>' for s in candidates)
    doc = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Free flood data workflow</title>
<style>body{{font:16px/1.55 system-ui;background:#f4f6f3;color:#16353b;margin:0}}main{{max-width:1080px;margin:auto;padding:30px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #bbc9c7}}.notice{{background:#fff0d2;padding:18px}}a{{color:#00697b}}li{{margin:12px 0}}.scroll{{overflow-x:auto}}</style><main>
<h1>Free flood data workflow</h1><p>Public metadata checked without an account or paid service. Existing local Python GIS tools perform analysis; exported GeoJSON layers can also be opened in QGIS.</p>
<p class="notice">No new flood accuracy result. This audit locates useful imagery, but no source here qualifies for precision or intersection-over-union scoring. Dorian observed high-water elevations remain hidden.</p>
<h2>Dorian: primary catalog corrects the discovery listing</h2><p>The ArcGIS listing's stated extent misses Hatteras. NOAA's {len(items):,}-tile catalog contains <b>{len(tiles)} tiles</b> intersecting our fixed 2 km domain, with {covered/domain_m.area:.1%} footprint coverage. Catalog rectangles do not establish cloud-free, valid image pixels.</p>
<p>Tile filename dates disagree with STAC timestamps. Neither date is silently substituted. Exact capture times and the apparent CC0/NLPL license discrepancy need primary-source review before a time-specific image analysis.</p>
<div class="scroll"><table><tr><th>Tile</th><th>STAC timestamp</th><th>Filename date hint</th><th>Conflict</th></tr>{rows}</table></div>
<h2>Evidence roles</h2><ul>{sources_html}</ul>
<h2>Local GIS review layers</h2><p><a href="dorian-domain.geojson">Fixed domain</a> · <a href="dorian-reference-locations.geojson">Reference locations without observed heights</a> · <a href="dorian-tile-footprints.geojson">Tile footprints with source image URLs</a> · <a href="source-audit.json">Audit, checksums and next steps</a></p>
<p>Use these layers to inspect event-era site context. Do not trace dry areas from blank image pixels or treat post-event dryness as evidence of dryness at flood peak.</p>
<p><a href="../dorian-2019/preflight.html">Dorian eligibility and boundary review</a> · <a href="../matthew-2016-domain4km/experiment-report.html">Running Matthew domain experiment</a></p></main></html>'''
    (ROOT/'index.html').write_text(doc, encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status','intersecting_tile_count','catalog_footprint_domain_fraction','valid_pixel_coverage_verified']}))


if __name__ == '__main__':
    main()
