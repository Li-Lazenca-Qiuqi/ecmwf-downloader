from types import SimpleNamespace
import pytest
import requests
from ecmwf_downloader.infrastructure import cds
from ecmwf_downloader.infrastructure.cds import CDSProvider, ProviderError, SubmissionUncertain

def response_error(code):
    response=requests.Response();response.status_code=code
    return requests.HTTPError('secret-key-do-not-expose',response=response)

def test_sdk_control_methods_do_not_download_and_disable_cleanup(monkeypatch):
    options={}
    class Client:
        def __init__(self,**kwargs): options.update(kwargs)
        def submit(self,*args): return SimpleNamespace(request_id='remote-1')
        def get_remote(self,*args): return SimpleNamespace(status='successful')
        def get_results(self,*args): return SimpleNamespace(asset={'href':'https://files.invalid/f.nc','file:size':42,'type':'application/x-netcdf'},location='https://files.invalid/f.nc')
        def retrieve(self,*args): pytest.fail('retrieve 会下载')
        def download_results(self,*args): pytest.fail('读取文件体')
    monkeypatch.setattr(cds,'DatastoresClient',Client)
    provider=CDSProvider({'key':'secret-key'})
    assert provider.submit('test',{})=='remote-1'
    status,assets=provider.inspect('remote-1')
    assert status=='successful' and assets[0]['size']==42
    assert options['cleanup'] is False and options['maximum_tries']==1

@pytest.mark.parametrize('code,exception',[(400,ProviderError),(403,ProviderError),(500,SubmissionUncertain),(408,SubmissionUncertain),(429,SubmissionUncertain)])
def test_submission_errors_distinguish_uncertainty_without_credentials(monkeypatch,code,exception):
    def submit(*args): raise response_error(code)
    monkeypatch.setattr(cds,'DatastoresClient',lambda **kwargs:SimpleNamespace(submit=submit))
    with pytest.raises(exception) as error: CDSProvider({'key':'secret-key'}).submit('test',{})
    assert 'secret-key' not in str(error.value)
    if exception is ProviderError: assert not isinstance(error.value,SubmissionUncertain)

def test_cancel_acknowledgement_alone_is_not_confirmed(monkeypatch):
    class Remote:
        status='running'
        def delete(self): return {'message':'cancellation accepted'}
    monkeypatch.setattr(cds,'DatastoresClient',lambda **kwargs:SimpleNamespace(get_remote=lambda *args:Remote()))
    with pytest.raises(ProviderError,match='确认'): CDSProvider({'key':'secret-key'}).cancel('remote-1')

def test_cancel_absent_remote_is_confirmed_and_expiry_is_explicit(monkeypatch):
    def remote(*args): raise response_error(404)
    monkeypatch.setattr(cds,'DatastoresClient',lambda **kwargs:SimpleNamespace(get_remote=remote))
    provider=CDSProvider({'key':'secret-key'})
    provider.cancel('remote-1')
    assert provider.inspect('remote-1')==('expired',[])

def test_attach_checks_dataset_and_parameters(monkeypatch):
    remote=SimpleNamespace(collection_id='other',request={})
    monkeypatch.setattr(cds,'DatastoresClient',lambda **kwargs:SimpleNamespace(get_remote=lambda *args:remote))
    with pytest.raises(ValueError): CDSProvider({'key':'secret-key'}).verify_request('remote','test',{})

@pytest.mark.parametrize("name,mime",[("actual.nc","application/x-netcdf"),("actual.grib","application/x-grib"),("actual.zip","application/zip")])
def test_result_names_and_types_follow_official_assets_without_rewriting(monkeypatch,name,mime):
    url="https://files.invalid/"+name
    result=SimpleNamespace(asset={"href":url,"file:size":100,"type":mime},location=url)
    client=SimpleNamespace(get_remote=lambda *args:SimpleNamespace(status="successful"),get_results=lambda *args:result)
    monkeypatch.setattr(cds,"DatastoresClient",lambda **kwargs:client)
    status,assets=CDSProvider({"key":"secret-key"}).inspect("remote")
    assert status=="successful" and assets[0]["filename"]==name and assets[0]["content_type"]==mime
