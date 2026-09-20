"""Recover the pre-Dorian profile from native PDF vectors, without inventing a datum tie.

Run with the bundled document Python (pdfplumber). The source page and colours
were visually reviewed; current-year points are checked against its numeric table.
"""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import json
from pathlib import Path

import pdfplumber

ROOT = Path('artifacts/validation/dorian-2019/bridge-geometry-review')
PDF = ROOT/'underwater-inspection-2023.pdf'


def main():
    with pdfplumber.open(PDF) as doc:
        page = doc.pages[79]
        text = page.extract_text()
        assert '6/10/2019' in text and 'Top of Rail = 0FT' in text
        assert page.width == 792 and page.height == 612
        black = [l for l in page.lines if l['stroking_color'] == (0., 0., 0.)]
        vertical = sorted({l['x0'] for l in black if l['height'] > 300 and l['width'] == 0})
        horizontal = sorted({l['top'] for l in black if l['width'] > 500 and l['height'] == 0 and l['top'] > 170})
        assert len(vertical) == 10 and len(horizontal) == 7
        x0, x90 = vertical[0], vertical[-1]
        y0, y15 = horizontal[0], horizontal[-1]
        def extract(color):
            vertices = []
            for line in page.lines:
                if line['stroking_color'] != color or line['top'] < 300:
                    continue
                for x, y in line['pts']:
                    point = (x, y)
                    if not vertices or vertices[-1] != point:
                        vertices.append(point)
            assert vertices
            return [{"distance_ft": (x-x0)*90/(x90-x0),
                         "sounding_ft_below_rail": (y-y0)*15/(y15-y0),
                         "pdf_xy": [x,y]} for x,y in vertices]
        old = extract((.58039,.19216,.68627))
        current = extract((0.,.58824,.24314))
    # Interior downstream soundings on PDF page 79; avoid bank/WS duplicate stations.
    table = [(10,10.9),(18.5,11),(27,11.5),(35.5,12.6),(44,11.9),
             (52.5,12.6),(61,11.2),(69.5,10.2),(78,9.6)]
    checks = []
    for distance, sounding in table:
        point = min(current,key=lambda p:abs(p['distance_ft']-distance))
        assert abs(point['distance_ft']-distance) < .01
        error = abs(point['sounding_ft_below_rail']-sounding)
        assert error < .01, (distance,error)
        checks.append({"distance_ft": distance, "table_sounding_ft": sounding, "error_ft": error})
    # Round to source-scale precision, retaining vector coordinates for independent audit.
    for point in old:
        point['distance_ft'] = round(point['distance_ft'],2)
        point['sounding_ft_below_rail'] = round(point['sounding_ft_below_rail'],2)
    result = {"status": 'relative_profile_extracted_not_terrain_admitted',
        "source_file": PDF.name, "source_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
        "source_page_one_based": 80, "survey_date": '2019-06-10',
        "reference": 'Top of existing bridge rail; positive soundings downwards',
        "vertical_datum": 'local rail reference; NAVD88 tie unresolved',
        "coordinates": 'Distance along downstream bridge profile; geographic endpoints unresolved',
        "source_precision": 'Digitized from vector plot; rounded to 0.01 ft is extraction precision, not survey accuracy',
        "vertices": old, "calibration": {"pdf_x_at_0_ft": x0,"pdf_x_at_90_ft": x90,
            "pdf_top_at_0_ft": y0,"pdf_top_at_15_ft": y15,"table_checks": checks},
        "benchmark_notes": ['2023 numeric table dates soundings June 12, while plot title says June 1. It is used only to verify plot-axis extraction.',
            'The 2023 table includes an undated highwater-mark note. It was incidentally exposed and is not used as Dorian truth.',
            'Only the June 2019 profile is a pre-Dorian geometry candidate; later curves are not substituted.',
            'Survey control confirms project NAVD88/GEOID G12NC, but does not identify the old rail elevation.',
            'Do not translate relative soundings to NAVD88 using an observed flood peak, unrelated water surface or proposed bridge height.',
            'One section does not define along-creek conveyance, bridge pressure flow or upstream/downstream bathymetry.'],
        "terrain_modified": False,"usgs_target_trace_values_read": False}
    (ROOT/'pre-dorian-profile.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({"vertices": len(old),"max_table_error_ft": max(c['error_ft'] for c in checks),"status": result['status']}))


if __name__ == '__main__': main()
