import hashlib
import json

import pytest

from scripts.verify_export import verify


def manifest(tmp_path):
    data='SPONGE · verified bytes'.encode()
    (tmp_path/'report.html').write_bytes(data)
    value={'schema':'sponge-export-manifest','version':1,'artifacts':[{'name':'report.html','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}]}
    path=tmp_path/'manifest.json';path.write_text(json.dumps(value))
    return path,value

def test_valid_then_modified_export(tmp_path):
    path,_=manifest(tmp_path);assert verify(path)==1
    (tmp_path/'report.html').write_bytes(b'changed')
    with pytest.raises(ValueError,match='mismatch'):verify(path)

@pytest.mark.parametrize('name',['../outside','C:secret','..\\outside','report.html/extra'])
def test_export_cannot_read_outside_directory(tmp_path,name):
    path,value=manifest(tmp_path);value['artifacts'][0]['name']=name;path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='filename'):verify(path)

def test_missing_and_duplicate_files(tmp_path):
    path,value=manifest(tmp_path);value['artifacts'].append(value['artifacts'][0]);path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='duplicate'):verify(path)
    value['artifacts']=value['artifacts'][:1];path.write_text(json.dumps(value));(tmp_path/'report.html').unlink()
    with pytest.raises(FileNotFoundError):verify(path)
