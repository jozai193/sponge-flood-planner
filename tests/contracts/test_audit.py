import hashlib
import json

import numpy as np
import pytest

from services.geodata.audit import audit_bundle


@pytest.fixture
def bundle(tmp_path):
    manifest = {'bundle_id': 'a'*64, 'location': [0, 0], 'grid': {'nx': 2, 'ny': 2, 'dx_m': 5, 'dy_m': 5},
                    'quality': {}, 'buildings': [], 'artifacts': [], 'sources': []}
    for name, values in [('z', np.zeros(4, dtype='<f4')), ('solid', np.zeros(4, dtype='u1'))]:
        raw=values.tobytes()
        (tmp_path/f'{name}.bin').write_bytes(raw)
        manifest['artifacts'].append({'name': name, 'sha256': hashlib.sha256(raw).hexdigest()})
    def save():
        (tmp_path/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    save()
    return tmp_path, manifest, save


@pytest.mark.parametrize('location', [[77.65,12.92],[-75.16,39.96],[151.2,-33.8],[0,0],[179.9,-20]])
def test_same_audit_rules_for_every_location(bundle, location):
    folder, manifest, save=bundle
    manifest['location']=location
    save()
    audit=audit_bundle(folder)
    checks={c['key']:c for c in audit['checks']}
    assert checks['integrity']['status']=='checked'
    assert checks['buildings']['status']=='unverified'  # zero records never means complete
    assert checks['resolution']['status']=='unknown'
    assert audit['quantitative_use']=='not_validated'
    assert audit['location']==location


def test_corrupt_array_is_reported(bundle):
    folder, _, _=bundle
    (folder/'z.bin').write_bytes(b'broken')
    assert audit_bundle(folder)['checks'][0]['status']=='failed'


def test_nonfinite_even_with_matching_hash_is_reported(bundle):
    folder, manifest, save=bundle
    raw=np.full(4,np.nan,dtype='<f4').tobytes()
    (folder/'z.bin').write_bytes(raw)
    manifest['artifacts'][0]['sha256']=hashlib.sha256(raw).hexdigest()
    save()
    assert audit_bundle(folder)['checks'][0]['status']=='failed'


def test_building_fidelity_distinguishes_provenance_from_verification(bundle):
    folder,manifest,save=bundle
    manifest['buildings']=[{'height_source':s} for s in [
        'provider height; not independently verified',
        'estimated from mapped floors at assumed 3 m per floor',
        'assumed display height','verified']]
    save()
    checks={c['key']:c for c in audit_bundle(folder)['checks']}
    assert '1 source-reported heights' in checks['heights']['detail']
    assert '1 heights estimated from floor counts' in checks['heights']['detail']
    assert '1 assumed or unknown heights' in checks['heights']['detail']
    assert checks['heights']['status']=='unverified'
    assert checks['appearance']['status']=='not_replicated'


def test_canonical_grid_alignment_resolves_building_and_candidate_picks(bundle):
    folder,manifest,save=bundle
    manifest['extent_m']=10
    manifest['grid'].update(crs='EPSG:32618',origin_x_m=500000,origin_y_m=4400000,
        row_direction='north',vertical_datum='NAVD88',elevation_origin_m=100)
    manifest['buildings']=[{'id':'b','geometry':{'type':'Polygon','coordinates':[[[-5,-5],[0,-5],[0,0],[-5,0],[-5,-5]]]},
        'base_elevation_m':1,'exterior_cells':[1],'height_source':'assumed display height'}]
    manifest['candidates']=[{'id':'site','x_m':2.5,'y_m':2.5,'cells':[3]}]
    save();checks={c['key']:c for c in audit_bundle(folder)['checks']}
    assert checks['alignment']['status']=='checked'
    assert 'EPSG:32618' in checks['alignment']['detail']
    manifest['candidates'][0]['cells']=[0];save()
    checks={c['key']:c for c in audit_bundle(folder)['checks']}
    assert checks['alignment']['status']=='failed'
