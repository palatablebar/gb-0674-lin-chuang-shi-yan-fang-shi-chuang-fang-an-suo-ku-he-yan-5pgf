from fastapi.testclient import TestClient
from app import main,store
from app.engine import evaluate
import pytest

def client(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DB_PATH',str(tmp_path/'test.sqlite'));return TestClient(main.app)
def test_api_idempotent(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);a=c.post('/api/runs',json={}).json();b=c.post('/api/runs',json={}).json();assert a['manifest']['run_id']==b['manifest']['run_id'];assert len(c.get('/api/runs').json())==1
def test_stale_review(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);a=c.post('/api/runs',json={}).json();url='/api/runs/'+a['manifest']['run_id']+'/review';assert c.post(url,json={'revision':1}).status_code==200;assert c.post(url,json={'revision':1}).status_code==409
def test_seven_entries(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    for k in main.MODULES:
        assert c.post('/api/'+k,json={}).status_code==200
        assert c.get('/'+k).status_code==200
def test_bad_dataset(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);assert c.post('/api/runs',json={'dataset':'../bad'}).status_code==422
def test_missing_run(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);assert c.get('/api/runs/none').status_code==404
def test_restart_store(tmp_path,sample):
    p=str(tmp_path/'durable.sqlite');store.save(p,sample);assert store.get(p,sample['manifest']['run_id'])['manifest']['sha256']==sample['manifest']['sha256']
def test_bad_revision(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);s=c.post('/api/runs',json={}).json();assert c.post('/api/runs/'+s['manifest']['run_id']+'/review',json={'revision':0}).status_code==422

def test_clean_navigation_run_preserved(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    run=c.post('/api/runs',json={'dataset':'clean'}).json()
    rid=run['manifest']['run_id']
    for k in main.MODULES:
        html=c.get('/'+k+'?run_id='+rid).text
        assert '?run_id='+rid in html
        assert rid in html
    assert c.get('/api/export/'+rid).status_code==200

def test_custom_csv_snapshot_and_navigation(tmp_path,monkeypatch):
    from app.config import ROOT
    c=client(tmp_path,monkeypatch)
    original=(ROOT/'sample_data/clean.csv').read_text()
    # 改成独立于所有仓内样例的证据编号，追踪其跨页与重跑行为。
    first=original.splitlines()[1].split(',')[0]
    custom=original.replace(first,first+'-CUSTOM')
    result=c.post('/api/runs',json={'csv_text':custom}).json()
    rid=result['manifest']['run_id']
    assert '-CUSTOM' in str(result['records']) or '-CUSTOM' in str(result['quarantine'])
    for key in main.MODULES:
        response=c.get('/'+key+'?run_id='+rid)
        assert response.status_code==200
        assert '?run_id='+rid in response.text
    repeated=c.post('/api/runs/'+rid+'/rerun',json={})
    assert repeated.status_code==200
    assert repeated.json()['manifest']['run_id']==rid
    assert repeated.json()['manifest']['sha256']==result['manifest']['sha256']

def test_rerun_adds_no_schedule_or_deviation(tmp_path,monkeypatch):
    # 重跑同一批：批号/窗口/锚点/偏离完全一致，不新增排期或偏离，不产生第二条批次
    c=client(tmp_path,monkeypatch)
    run=c.post('/api/runs',json={}).json();rid=run['manifest']['run_id']
    rerun=c.post('/api/runs/'+rid+'/rerun',json={}).json()
    assert rerun['manifest']['run_id']==rid
    assert rerun['windows']==run['windows']
    assert rerun['anchors']==run['anchors']
    assert rerun['deviations']==run['deviations']
    assert len(c.get('/api/runs').json())==1

def test_rerun_failure_keeps_previous_conclusion(tmp_path,monkeypatch):
    # 重算失败：旧批结论原样保留，接口 409，不覆盖也不新增批次
    c=client(tmp_path,monkeypatch)
    run=c.post('/api/runs',json={'dataset':'clean'}).json();rid=run['manifest']['run_id']
    from app import engine
    def boom(*a,**k):
        from app.errors import BusinessError
        raise BusinessError('BROKEN_CSV','模拟重算损坏')
    monkeypatch.setattr(engine,'evaluate',boom)
    response=c.post('/api/runs/'+rid+'/rerun',json={})
    assert response.status_code==409
    assert response.json()['code']=='RERUN_FAILED'
    kept=c.get('/api/runs/'+rid).json()
    assert kept['manifest']['sha256']==run['manifest']['sha256']
    assert kept['balance']['status']=='可锁库'
    assert len(c.get('/api/runs').json())==1

def test_anchor_module_in_pipeline_and_pages(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    assert c.post('/api/anchor',json={}).status_code==200
    run=c.post('/api/runs',json={}).json()
    html=c.get('/anchor?run_id='+run['manifest']['run_id']).text
    assert '排期锚点裁决' in html and 'ACTUAL_FIRST' in html
