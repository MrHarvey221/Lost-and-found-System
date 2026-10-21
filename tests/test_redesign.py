import base64
from datetime import date
from hashlib import pbkdf2_hmac
from io import BytesIO
import json
import sqlite3
from types import SimpleNamespace as Item
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, func, select
from config import ROOT, Settings
from database import session_factory
from main import create_app
from matching import MatchEngine, score_pairs
from migrations import legacy_models
import models
from conftest import PASSWORD, report, claim


def bottle_pair():
    lost=Item(title='Pink two-litre bottle',description='Large pink two-litre drinking bottle lost near the university library.',category='Drinkware',colour='Pink',brand='',location_lost='University library',date_lost=date(2026,1,2))
    found=Item(title='Reusable water container',description='Rose-coloured reusable water flask discovered beside the campus study area.',category='Drinkware',colour='Rose',brand='',location_found='Campus study area',date_found=date(2026,1,4))
    return lost,found


def test_different_vocabulary_is_a_plausible_fallback_match():
    lost,found=bottle_pair();_,score,detail=score_pairs(lost,[found])[0]
    assert 45<=score<100
    assert 'Similar colour' in detail['reasons']
    assert detail['mode']=='fallback' and detail['semantic']['weight']==0


def test_sentence_model_mode_and_real_embedding_when_installed():
    model=ROOT/'models'/'all-MiniLM-L6-v2'
    if not (model/'modules.json').exists():pytest.skip('Optional pretrained model has not been downloaded.')
    engine=MatchEngine('auto',model)
    assert engine.status()['mode']=='semantic',engine.status()
    lost,found=bottle_pair();_,score,detail=engine.score_pairs(lost,[found])[0]
    assert score>=45 and detail['semantic']['similarity']>.4
    assert detail['mode']=='semantic' and detail['semantic']['weight']==30


def test_missing_model_falls_back_honestly(tmp_path):
    engine=MatchEngine('auto',tmp_path/'missing-model')
    assert engine.status()['mode']=='fallback'
    lost,found=bottle_pair()
    assert engine.score_pairs(lost,[found])[0][2]['semantic']['weight']==0


def test_strong_contradictions_reduce_the_score():
    lost,found=bottle_pair()
    found.title='Blue Adidas backpack';found.description='Blue Adidas school bag found near the sports fields.'
    found.category='Bags';found.colour='Blue';found.brand='Adidas'
    assert score_pairs(lost,[found])[0][1]<30
    # Even generic shared words and broad category equality cannot hide a conflict.
    lost.category=found.category='Other'
    assert score_pairs(lost,[found])[0][1]<30
    lost.title='Black Samsung smartphone';lost.description='Black Samsung smartphone.'
    lost.category='Electronics';lost.colour='Black';lost.brand='Samsung'
    found.category='Bags'
    assert score_pairs(lost,[found])[0][1]<30


@pytest.mark.parametrize('first',['lost','found'])
def test_delayed_and_reverse_reports_notify_the_right_people_once(campus,first):
    student,finder,officer=campus['clients'][:3]
    lost,found=bottle_pair()
    def lost_report():return report(student,'lost',title=lost.title,category=lost.category,description=lost.description,colour=lost.colour,brand='',location_lost=lost.location_lost,date_lost='2026-01-02')
    def found_report():return report(finder,'found',title=found.title,category=found.category,description=found.description,colour=found.colour,brand='',location_found=found.location_found,date_found='2026-01-04',storage_location='Campus security shelf B2')
    if first=='lost':lost_report();assert student.get('/api/matches').json()==[];found_report()
    else:found_report();assert finder.get('/api/matches').json()==[];lost_report()
    matches=student.get('/api/matches').json();assert len(matches)==1
    mid=matches[0]['match_id'];assert matches[0]['similarity_score']>=45
    notes=student.get('/api/notifications').json();matching=[n for n in notes if n['match_id']==mid]
    assert len(matching)==1 and 'Good news!' in matching[0]['message_summary']
    assert student.get('/api/matches/'+str(mid)).status_code==200
    assert finder.get('/api/matches/'+str(mid)).status_code==200
    assert len([n for n in finder.get('/api/notifications').json() if n['match_id']==mid])==1
    for _ in range(2):assert officer.post('/api/matches/recheck').status_code==200
    assert len([n for n in student.get('/api/notifications').json() if n['match_id']==mid])==1
    stranger=TestClient(campus['app'],headers={'X-Findly-Request':'1'})
    try:
        assert stranger.post('/api/auth/register',json={'name':'Unrelated','email':'unrelated@example.com','password':PASSWORD}).status_code==201
        assert stranger.get('/api/matches/'+str(mid)).status_code==404
        assert not any(n['match_id']==mid for n in stranger.get('/api/notifications').json())
    finally:stranger.close()


def test_four_photographs_are_saved_and_protected(campus):
    student,finder=campus['clients'][:2];found=report(finder,'found')
    stream=BytesIO();Image.new('RGB',(32,32),'pink').save(stream,format='PNG');photo=stream.getvalue()
    response=finder.post(f"/api/reports/found/{found['record_id']}/photos",files=[('files',(f'view-{i}.png',photo,'image/png')) for i in range(4)])
    assert response.status_code==201,response.text
    urls=response.json()['image_urls'];assert len(urls)==4
    for url in urls:assert student.get(url).status_code==200
    assert student.post(f"/api/reports/found/{found['record_id']}/photos",files=[('files',('fake.png',photo,'image/png'))]).status_code==403
    invalid=finder.post(f"/api/reports/found/{found['record_id']}/photos",files=[('files',(f'view-{i}.png',photo,'image/png')) for i in range(5)])
    assert invalid.status_code==422


def test_recovery_updates_only_the_claimants_linked_lost_report(campus):
    student,finder,officer=campus['clients'][:3]
    lost=report(student);other=report(student,title='Another lost sleeve');found=report(finder,'found')
    response=student.post('/api/claims',json={'found_item_id':found['record_id'],'lost_item_id':lost['record_id'],
        'claim_statement':'This is my sleeve lost near the library.','private_description':'Yellow stitching on the inside pocket.'})
    assert response.status_code==201,response.text
    cid=response.json()['claim_id']
    assert officer.patch(f'/api/claims/{cid}/review',json={'decision':'approved','reviewer_notes':'Verified the private yellow stitching.'}).status_code==200
    assert officer.patch(f"/api/reports/found/{found['record_id']}/status",json={'status':'returned','reason':'Collected by the verified owner at the security desk.'}).status_code==200
    assert student.get(f"/api/reports/lost/{lost['record_id']}").json()['status']=='returned'
    assert student.get(f"/api/reports/lost/{other['record_id']}").json()['status']=='reported'


def test_old_running_integration_preserves_accounts_titles_and_inline_photos(tmp_path):
    path=tmp_path/'running.db';url='sqlite:///'+str(path)
    engine=create_engine(url);legacy_models.Base.metadata.create_all(engine)
    stream=BytesIO();Image.new('RGB',(16,16),'pink').save(stream,format='PNG')
    inline='data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()
    with session_factory(engine)() as db:
        user=legacy_models.User(name='Existing',surname='Student',email='preserved@example.com',role='student');db.add(user);db.flush()
        db.add(legacy_models.LostItem(reporter_id=user.user_id,category='Drinkware',description='Original pink water bottle',colour='Pink',location_lost='Library',date_lost=date(2026,1,2),image_ref=inline));db.commit()
    engine.dispose()
    password='Legacy123';salt='0123456789abcdef';digest=pbkdf2_hmac('sha256',password.encode(),salt.encode(),310000).hex()
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE account_credentials(user_id INTEGER PRIMARY KEY REFERENCES users(user_id),password_hash VARCHAR NOT NULL,campus VARCHAR)')
        db.execute('INSERT INTO account_credentials VALUES (1,?,?)',(salt+':'+digest,'Original Campus'))
        db.execute('CREATE TABLE item_details(item_key VARCHAR PRIMARY KEY,title VARCHAR NOT NULL,created DATETIME)')
        db.execute("INSERT INTO item_details VALUES ('L-1','My original bottle','2026-01-02 12:30:00')")
        db.commit()
    settings=Settings(database_url=url,data_dir=tmp_path/'files',session_secret='legacy-migration-test-'*3,semantic_mode='off')
    with TestClient(create_app(settings),headers={'X-Findly-Request':'1'}) as client:
        response=client.post('/api/auth/login',json={'email':'preserved@example.com','password':password})
        assert response.status_code==200,response.text
        assert response.json()['campus']=='Original Campus'
        item=client.get('/api/reports').json()[0]
        assert item['title']=='My original bottle' and item['description']=='Original pink water bottle'
        assert client.get(item['image_url']).status_code==200
        with client.app.state.sessions() as db:
            assert db.get(models.User,1).password_hash.startswith('pbkdf2_sha256$600000$')
            assert not db.get(models.LostItem,1).image_ref.startswith('data:')
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM account_credentials').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM users').fetchone()[0]==1
    assert list((tmp_path/'backups').glob('*.db'))


def test_demo_is_idempotent_and_uses_actual_matching(campus,monkeypatch):
    import demo
    monkeypatch.setattr(demo,'make_illustrations',lambda:None)
    with campus['app'].state.sessions() as db:
        before=db.scalar(select(func.count()).select_from(models.User))
        demo.seed_demo(db,MatchEngine('off'))
        users=db.scalar(select(func.count()).select_from(models.User));matches=db.scalar(select(func.count()).select_from(models.Match))
        demo.seed_demo(db,MatchEngine('off'))
        assert users==before+4 and matches>0
        assert db.scalar(select(func.count()).select_from(models.User))==users
        assert db.scalar(select(func.count()).select_from(models.Match))==matches
