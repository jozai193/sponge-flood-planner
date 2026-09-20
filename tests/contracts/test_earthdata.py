import httpx
import pytest

from services.geodata import earthdata

URL='https://gpm1.gesdisc.eosdis.nasa.gov/data/3IMERG.20240101-S000000-E002959.V07B.HDF5'
HDF=b'\x89HDF\r\n\x1a\nfixture'

def test_download_redirect_and_cache_integrity(tmp_path,monkeypatch):
    monkeypatch.setattr(earthdata,'CACHE',tmp_path)
    requests=[]
    def handler(request):
        requests.append(request)
        assert request.headers['authorization']=='Bearer test-token'
        if request.url.host.startswith('gpm1'):
            return httpx.Response(302,headers={'location':'https://gpm2.gesdisc.eosdis.nasa.gov/file'})
        return httpx.Response(200,content=HDF)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        path,source=earthdata.download(URL,'test-token',client)
        assert path.read_bytes()==HDF and source['bytes']==len(HDF)
        earthdata.download(URL,'test-token',client)
        assert len(requests)==2
        path.write_bytes(b'corrupt')
        earthdata.download(URL,'test-token',client)
        assert path.read_bytes()==HDF and len(requests)==4
        path.with_name('source.json').write_text('{broken')
        earthdata.download(URL,'test-token',client)
        assert path.read_bytes()==HDF and len(requests)==6

def test_redirect_never_forwards_token_to_foreign_host(tmp_path,monkeypatch):
    monkeypatch.setattr(earthdata,'CACHE',tmp_path)
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(302,headers={'location':'https://example.com/data'})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client, pytest.raises(ValueError,match='credentials were not forwarded'):
        earthdata.download(URL,'test-token',client)
    assert len(requests)==1


def test_redirect_without_location_is_reported_cleanly(tmp_path,monkeypatch):
    monkeypatch.setattr(earthdata,'CACHE',tmp_path)
    with httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(302))) as client, pytest.raises(ValueError,match='omitted a location'):
        earthdata.download(URL,'test-token',client)

@pytest.mark.parametrize('status,body,match',[(403,b'', 'access denied'),(200,b'<html>Login</html>','invalid HDF5')])
def test_invalid_download_is_not_committed(tmp_path,monkeypatch,status,body,match):
    monkeypatch.setattr(earthdata,'CACHE',tmp_path)
    with httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(status,content=body))) as client, pytest.raises(ValueError,match=match):
        earthdata.download(URL,'test-token',client)
    assert not list(tmp_path.rglob('*.HDF5'))
    assert not list(tmp_path.rglob('*.partial'))

def test_missing_token_preserves_catalog(monkeypatch):
    monkeypatch.setattr(earthdata.settings,'earthdata_token',None)
    catalog={'granules':[]}
    assert earthdata.acquire(catalog,{}) is catalog


def test_current_nasa_data_host_is_allowed():
    assert earthdata.trusted_nasa("https://data.gesdisc.earthdata.nasa.gov/data/file.HDF5")
    assert not earthdata.trusted_nasa("https://data.gesdisc.earthdata.nasa.gov.example.com/file")


def test_nasa_cdn_redirect_omits_bearer(tmp_path,monkeypatch):
    monkeypatch.setattr(earthdata,'CACHE',tmp_path)
    def handler(request):
        if request.url.host=='d2b3c3wh8s6en5.cloudfront.net':
            assert 'authorization' not in request.headers
            return httpx.Response(200,content=HDF)
        assert request.headers['authorization']=='Bearer test-token'
        return httpx.Response(303,headers={'location':'https://d2b3c3wh8s6en5.cloudfront.net/file?Signature=fixture'})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        path,meta=earthdata.download(URL,'test-token',client)
        assert path.read_bytes()==HDF
        assert 'Signature' not in str(meta)
    with pytest.raises(ValueError,match='approved NASA'):
        earthdata.download('https://d2b3c3wh8s6en5.cloudfront.net/V07.HDF5','test-token',client)
