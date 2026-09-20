"""Read native terrain at fixed HWM coordinates; never move or fit observations."""
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds

ROOT = Path('artifacts/validation/sandy-2012')
URL = 'https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/NY_CMPG_2013/TIFF/USGS_one_meter_x58y451_NY_CMPG_2013.tif'


def main():
    assessment = json.loads((ROOT / 'accuracy.json').read_text())
    features = json.loads((ROOT / 'observations-64.geojson').read_text())['features']
    runs = {r['grid_cells']: {s['observation_id']: s for s in r['samples']} for r in assessment['runs']}
    rows = []
    with rasterio.Env(GDAL_HTTP_TIMEOUT='60', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                      CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'), rasterio.open(URL) as src:
        transform = Transformer.from_crs(4269, src.crs, always_xy=True)
        for feature in features:
            props = feature['properties']
            x, y = transform.transform(*feature['geometry']['coordinates'])
            native = float(next(src.sample([(x, y)]))[0])
            if not np.isfinite(native) or native == src.nodata:
                raise ValueError('Missing native point terrain')
            item = {'id': props['id'], 'site_id': props['site_id'],
                        'observed_navd88_m': props['water_elevation_m'],
                        'native_ground_navd88_m': native,
                        'native_ground_above_observation_m': native-props['water_elevation_m'],
                        'description': props['location_description'], 'neighborhoods': []}
            for radius in (5, 15, 30):
                window = from_bounds(x-radius, y-radius, x+radius, y+radius, src.transform)
                a = src.read(1, window=window, masked=True).compressed()
                a = a[np.isfinite(a)]
                if not len(a):
                    raise ValueError('Missing neighborhood terrain')
                item['neighborhoods'].append({'half_width_m': radius,
                    'count': len(a), 'min_m': float(a.min()), 'p10_m': float(np.quantile(a, .1)),
                    'median_m': float(np.median(a)), 'max_m': float(a.max()),
                    'fraction_below_observed_water': float(np.mean(a < props['water_elevation_m']))})
            item['model_grids'] = {str(n): {key: samples[props['id']][key] for key in
                ('ground_elevation_m', 'status', 'row', 'col')} for n, samples in runs.items()}
            rows.append(item)
    result = {'source_url': URL, 'source_acquisition': '2013 (post-event)',
        'assessment_sha256': hashlib.sha256((ROOT/'accuracy.json').read_bytes()).hexdigest(),
        'method': 'Native containing pixel and fixed square neighborhoods at original NAD83 coordinates. Neighborhoods are diagnostics, not alternative prediction samples or confidence intervals.',
        'limitation': 'Map-position uncertainty has no supplied radius; 5/15/30 m are sensitivity distances only. A source-ground conflict does not distinguish positional error from terrain change.',
        'observations': rows}
    (ROOT/'terrain-diagnosis.json').write_text(json.dumps(result, indent=2))
    for r in rows:
        print(r['id'], 'native ground minus observed water:', round(r['native_ground_above_observation_m'], 3), 'm')


if __name__ == '__main__':
    main()
