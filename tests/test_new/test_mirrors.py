from pathlib import Path
from contextlib import nullcontext
from types import SimpleNamespace
import pytest
from ecmwf_downloader.infrastructure import mirrors
from ecmwf_downloader.application.datasets import DatasetService
from ecmwf_downloader.application.request_builder import RequestBuilder
from ecmwf_downloader.domain.models import SplitStrategy

KEY='e5.oper.an.sfc/202401/e5.oper.an.sfc.128_167_2t.ll025sc.2024010100_2024013123.nc'
def test_gdex_lists_own_catalogue_and_rejects_foreign_paths(monkeypatch):
    xml = f'''<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
      <dataset urlPath="files/d633000/{KEY}"><dataSize units="Mbytes">12.3</dataSize></dataset>
      <dataset urlPath="files/d633000/{KEY}" />
      <dataset urlPath="https://untrusted.invalid/{KEY}" />
      <dataset urlPath="files/d633000/e5.oper.an.pl/202401/other.nc" />
    </catalog>'''
    class Response:
        content = xml.encode()
        def raise_for_status(self): pass
    calls = []
    def get(url, **kwargs): calls.append(url);return Response()
    monkeypatch.setattr(mirrors, 'request_session', lambda _network: nullcontext(SimpleNamespace(get=get)))
    result = mirrors.gdex_schema()
    assert calls == [f'{mirrors.GDEX_CATALOG_URL}/{mirrors.DEFAULT_PREFIX}catalog.xml']
    assert result['collection_id'] == mirrors.GDEX_ID and result['source_url'] == mirrors.GDEX_URL
    assert result['fields'][0]['options'] == [{'value': KEY, 'label': f'{Path(KEY).name} (12.3 Mbytes)'}]
    with pytest.raises(ValueError): mirrors.gdex_schema('../private/')
    with pytest.raises(ValueError): mirrors.gdex_schema('e5.oper.invariant/197901/')


def test_ncar_complete_listing_deduplicates_pages_and_keeps_sizes(monkeypatch):
    calls=[]
    class Session:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def get(self,url,params,**kwargs):
            calls.append(params)
            second=len(calls)>1
            xml=f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><IsTruncated>{str(not second).lower()}</IsTruncated><NextContinuationToken>next</NextContinuationToken><Contents><Key>{KEY}</Key><Size>100</Size></Contents></ListBucketResult>'
            class Response:
                content=xml.encode()
                def raise_for_status(self): pass
            return Response()
    monkeypatch.setattr(mirrors, 'request_session', lambda _network: Session())
    result=mirrors.ncar_schema()
    assert result['fields'][0]['options'][0]['size_bytes']==100
    assert len(result['fields'][0]['options'])==1
    assert calls[1]['continuation-token']=='next'
    with pytest.raises(ValueError): mirrors.ncar_schema('https://untrusted.invalid/')


@pytest.mark.parametrize('source,base',[(mirrors.NCAR_ID,mirrors.NCAR_URL),(mirrors.GDEX_ID,mirrors.GDEX_URL)])
def test_mirror_links_only_use_head_never_file_get(monkeypatch,source,base):
    calls=[]
    class Response:
        headers={'Content-Length':'123','Content-Type':'application/x-netcdf'}
        url=base+'/'+KEY
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def raise_for_status(self): pass
    def head(url,**kwargs):
        calls.append(url);return Response()
    monkeypatch.setattr(mirrors, 'request_session', lambda _network: nullcontext(SimpleNamespace(
        head=head, get=lambda *args, **kwargs: pytest.fail('读取文件体'),
    )))
    result=mirrors.MirrorProvider().results(source,{'object_key':KEY})
    assert calls==[base+'/'+KEY] and result[0]['size']==123
    assert not hasattr(mirrors.MirrorProvider,'download')
    plans=RequestBuilder().build(dataset_id=source,payload={'object_key':[KEY,KEY]})
    assert len(plans)==1 and plans[0].payload=={'object_key':KEY}
    with pytest.raises(ValueError): RequestBuilder().build(dataset_id=source,payload={'object_key':[KEY]},strategy=SplitStrategy.DAY)

def test_arco_export_and_catalogue_are_unavailable():
    assert not hasattr(mirrors,'arco_schema') and not hasattr(mirrors,'arco_store')
    assert mirrors.ARCO_ID not in mirrors.MIRROR_IDS
    with pytest.raises(ValueError,match='移除'): DatasetService().list(source='arco')
    with pytest.raises(ValueError,match='移除'): DatasetService().schema(mirrors.ARCO_ID)
    with pytest.raises(ValueError,match='移除'): RequestBuilder().build(dataset_id=mirrors.ARCO_ID,payload={})
