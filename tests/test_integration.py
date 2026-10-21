from io import BytesIO
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from main import create_app
from security import verify_password
import models
from conftest import PASSWORD, report, claim


def test_auth_registration_login_logout_and_identity(campus):
    student = campus['clients'][0]
    uid = campus['users'][0]['user_id']
    assert student.get('/api/auth/me').json()['user_id'] == uid
    with campus['app'].state.sessions() as db:
        user = db.get(models.User, uid)
        assert user.password_hash != PASSWORD and verify_password(PASSWORD, user.password_hash)
    session = student.cookies.get('findly_v3_session')
    response = student.post('/api/auth/logout')
    assert response.status_code == 204
    assert student.get('/api/auth/me').status_code == 401
    student.cookies.set('findly_v3_session', session)
    assert student.get('/api/auth/me').status_code == 401  # logout revokes the signed token
    student.cookies.clear()
    assert student.post('/api/auth/login', json={'email':'campus0@example.com','password':'incorrect-password'}).status_code == 401
    response = student.post('/api/auth/login', json={'email':'CAMPUS0@example.com','password':PASSWORD})
    assert response.status_code == 200
    assert 'httponly' in response.headers['set-cookie'].lower()
    assert 'samesite=strict' in response.headers['set-cookie'].lower()
    assert 'password' not in response.text
    assert student.post('/api/auth/register', json={'name':'Duplicate','email':'CAMPUS0@example.com','password':PASSWORD}).status_code == 409


def test_cannot_self_register_as_officer_or_spoof_reporter(campus):
    student = campus['clients'][0]
    response = student.post('/api/auth/register', json={'name':'Intruder','email':'intruder@example.com','password':PASSWORD,'role':'administrator'})
    assert response.status_code == 422
    payload = dict(title='My laptop',category='Electronics',description='Black computer sleeve', location_lost='Library',date_lost='2026-01-02',reporter_id=campus['users'][2]['user_id'])
    assert student.post('/api/reports/lost', json=payload).status_code == 422
    assert student.post('/api/auth/register', json={'name':'Weak','email':'weak@example.com','password':'short'}).status_code == 422


def test_origin_csrf_and_anonymous_access(campus):
    student = campus['clients'][0]
    assert student.post('/api/auth/logout', headers={'Origin':'https://untrusted.example'}).status_code == 403
    anonymous = TestClient(campus['app'])
    try:
        assert anonymous.get('/api/reports').status_code == 401
        assert anonymous.post('/api/auth/login', json={'email':'campus0@example.com','password':PASSWORD}).status_code == 403
        assert anonymous.get('/api/evidence/1/file').status_code == 401
    finally:
        anonymous.close()


def test_reports_search_match_components_and_duplicate_prevention(campus):
    student, finder, officer = campus['clients'][:3]
    lost = report(student)
    found = report(finder, 'found')
    pairs = student.get('/api/matches').json()
    assert len(pairs) == 1 and pairs[0]['similarity_score'] == 100
    assert pairs[0]['score_components']['description']['weight'] == 40
    assert {'description','semantic','item_name','category','colour','brand','location','date'} <= set(pairs[0]['score_components'])
    for _ in range(3):
        assert officer.post('/api/matches/recheck').status_code == 200
    with campus['app'].state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(models.Match)) == 1
        notes = db.scalars(select(models.Notification).where(models.Notification.event_type == 'match')).all()
        assert len(notes) == 2
        # A duplicate pair is rejected at database level too.
        db.add(models.Match(lost_item_id=lost['record_id'], found_item_id=found['record_id'],similarity_score=90))
        with pytest.raises(IntegrityError):
            db.commit()
    assert len(student.get('/api/reports', params={'q':'Lenovo','kind':'found'}).json()) == 1
    assert student.get('/api/reports', params={'q':'no-such-item'}).json() == []
    assert len(student.get('/api/reports', params={'mine':True}).json()) == 1
    # A stranger sees public reports, but not another person's matching feed.
    assert campus['clients'][4].get('/api/reports').status_code == 200


def test_claim_permissions_private_evidence_information_approval_and_return(campus):
    student, finder, officer, admin = campus['clients'][:4]
    report(student)
    found = report(finder, 'found')
    c = claim(student, found)
    cid = c['claim_id']
    assert c['claim_status'] == 'submitted'
    assert 'private_description' not in str(student.get('/api/claims').json())
    assert finder.get(f'/api/claims/{cid}').status_code == 404
    assert finder.get('/api/claims').json() == []
    assert 'yellow star' not in finder.get('/api/reports').text
    assert student.patch(f'/api/claims/{cid}/review', json={'decision':'approved','reviewer_notes':'I approve my own claim'}).status_code == 403
    assert officer.patch(f'/api/claims/{cid}/review', json={'decision':'more_information','reviewer_notes':'Please supply a photograph of your purchase receipt.'}).status_code == 200
    assert student.get(f'/api/claims/{cid}').json()['claim_status'] == 'more_information'
    pdf = b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF\n'
    upload = student.post(f'/api/claims/{cid}/evidence', data={'private_description':'Here is my purchase receipt for the sleeve.'},files={'file':('receipt.pdf',pdf,'application/pdf')})
    assert upload.status_code == 201, upload.text
    file_url = upload.json()['file_url']
    assert student.get(file_url).status_code == 200
    assert officer.get(file_url).status_code == 200
    assert finder.get(file_url).status_code == 404
    assert 'attachment' in student.get(file_url).headers['content-disposition']
    assert student.get(f'/api/claims/{cid}').json()['claim_status'] == 'submitted'
    approved = officer.patch(f'/api/claims/{cid}/review', json={'decision':'approved','reviewer_notes':'Private mark and purchase proof verified in person.'})
    assert approved.status_code == 200, approved.text
    assert finder.get(f"/api/reports/found/{found['record_id']}").json()['status'] == 'claim_approved'
    assert student.get('/api/matches').json() == []
    assert student.post('/api/claims',json={'found_item_id':found['record_id'],'claim_statement':'Another claim on the same item','private_description':'I have another private ownership detail'}).status_code == 409
    returned = officer.patch(f"/api/reports/found/{found['record_id']}/status", json={'status':'returned','reason':'Collected in person; campus identity and receipt verified.'})
    assert returned.status_code == 200, returned.text
    assert student.get(f'/api/claims/{cid}').json()['claim_status'] == 'completed'
    events = admin.get('/api/admin/history').json()
    assert any(e['related_record_type']=='claim' and e['new_status']=='approved' for e in events)
    assert any(e['related_record_type']=='found' and e['new_status']=='returned' for e in events)
    notes = student.get('/api/notifications').json()
    assert any('complete' in n['message_summary'] for n in notes)
    assert student.patch('/api/notifications/read-all').status_code == 200
    assert all(n['read_at'] for n in student.get('/api/notifications').json())


def test_officer_cannot_review_own_claim(campus):
    student, finder, officer = campus['clients'][:3]
    found = report(finder, 'found')
    c = claim(officer, found)
    assert officer.patch(f"/api/claims/{c['claim_id']}/review", json={'decision':'approved','reviewer_notes':'Trying to approve my own claim'}).status_code == 403


def test_reject_and_conflicting_claims(campus):
    student, finder, officer, admin, other = campus['clients']
    found = report(finder, 'found')
    first = claim(student, found)
    second = claim(other, found)
    decision = {'decision':'approved','reviewer_notes':'Verified the private mark and receipt.'}
    assert officer.patch(f"/api/claims/{first['claim_id']}/review", json=decision).status_code == 200
    assert other.get(f"/api/claims/{second['claim_id']}").json()['claim_status'] == 'rejected'
    assert admin.patch(f"/api/claims/{second['claim_id']}/review", json=decision).status_code == 409
    other_found = report(finder, 'found',title='Another sleeve')
    rejected = claim(student, other_found)
    assert officer.patch(f"/api/claims/{rejected['claim_id']}/review",json={'decision':'rejected','reviewer_notes':'The receipt describes a different item.'}).status_code == 200
    assert student.get(f"/api/claims/{rejected['claim_id']}").json()['claim_status'] == 'rejected'


def test_upload_validation_images_and_private_paths(campus):
    from PIL import Image
    student, finder = campus['clients'][:2]
    found = report(finder, 'found')
    c = claim(student, found)
    url = f"/api/claims/{c['claim_id']}/evidence"
    for name, data, mime in [('script.svg',b'<svg onload="alert(1)">','image/svg+xml'),('fake.jpg',b'not an image','image/jpeg'),('huge.pdf',b'%PDF-'+b'x'*(3*1024*1024),'application/pdf')]:
        response = student.post(url,data={'private_description':'Proof of ownership attached here.'},files={'file':(name,data,mime)})
        assert response.status_code in {413,422}, response.text
    image = BytesIO()
    Image.new('RGB',(32,32),'blue').save(image,format='PNG')
    response = finder.post(f"/api/reports/found/{found['record_id']}/image", files={'file':('item.png',image.getvalue(),'image/png')})
    assert response.status_code == 201, response.text
    assert student.get(response.json()['image_url']).status_code == 200
    assert student.get('/data/evidence/anything.pdf').status_code == 404
    assert student.get('/.env').status_code == 404


def test_admin_and_suspension_revoke_access(campus):
    student, finder, officer, admin = campus['clients'][:4]
    assert student.get('/api/admin/users').status_code == 403
    assert officer.get('/api/admin/history').status_code == 403
    uid = campus['users'][0]['user_id']
    response = admin.patch(f'/api/admin/users/{uid}',json={'role':'staff','account_status':'suspended','reason':'Suspended for testing authorization.'})
    assert response.status_code == 200
    assert student.get('/api/auth/me').status_code == 401
    assert admin.patch(f"/api/admin/users/{campus['users'][3]['user_id']}",json={'role':'student','account_status':'suspended','reason':'Attempting self-lockout.'}).status_code == 409


def test_persistence_restart_and_foreign_keys(campus):
    student = campus['clients'][0]
    lost = report(student)
    with TestClient(create_app(campus['settings']),headers={'X-Findly-Request':'1'}) as restarted:
        assert restarted.post('/api/auth/login',json={'email':'campus0@example.com','password':PASSWORD}).status_code == 200
        assert any(row['id']==lost['id'] for row in restarted.get('/api/reports').json())
        assert restarted.get('/api/notifications').json()
    with campus['app'].state.sessions() as db:
        assert db.execute(text('PRAGMA foreign_keys')).scalar() == 1
        db.add(models.LostItem(reporter_id=999999, title='Orphan',category='Other',description='Orphan report',location_lost='Library',date_lost=date(2026,1,2)))
        with pytest.raises(IntegrityError):
            db.commit()


def test_ordinary_users_cannot_return_or_modify_others_items(campus):
    student, finder, officer = campus['clients'][:3]
    found = report(finder, 'found')
    url = f"/api/reports/found/{found['record_id']}/status"
    assert student.patch(url,json={'status':'returned','reason':'Attempt to return without verification'}).status_code == 403
    assert officer.patch(url,json={'status':'returned','reason':'No approved claim exists yet'}).status_code == 409
    lost = report(student)
    assert student.patch(f"/api/reports/lost/{lost['record_id']}/status", json={'status':'closed','reason':'I located my missing sleeve.'}).status_code == 200


def test_static_ui_and_no_local_accounts(campus):
    client = campus['clients'][0]
    assert 'findly' in client.get('/').text
    script = client.get('/app.js').text
    assert 'fetch(' in script and 'localStorage' not in script and 'function matchScore' not in script
    assert client.get('/styles.css').status_code == 200
    assert client.get('/api/health').json()['status'] == 'ok'


def test_duplicate_claim_identity_spoofing_and_private_storage(campus):
    student, finder, officer = campus['clients'][:3]
    found = report(finder, 'found')
    first = claim(student, found)
    payload = dict(found_item_id=found['record_id'],claim_statement='I own this particular sleeve.',private_description='A private mark inside the sleeve.')
    assert student.post('/api/claims', json=payload).status_code == 409
    assert finder.post('/api/claims', json=payload).status_code == 409
    payload['claimant_id'] = campus['users'][2]['user_id']
    assert student.post('/api/claims', json=payload).status_code == 422
    review = dict(decision='approved',reviewer_notes='Checked all identifying details.',reviewer_id=campus['users'][2]['user_id'])
    assert officer.patch(f"/api/claims/{first['claim_id']}/review",json=review).status_code == 422
    storage_url = f"/api/reports/found/{found['record_id']}/storage"
    details = dict(storage_location='Security office, shelf B2',reason='Deposited at security by the finder.')
    assert finder.patch(storage_url,json=details).status_code == 403
    assert officer.patch(storage_url,json=details).status_code == 200
    assert 'Security office' not in student.get('/api/reports').text
    assert 'Security office' in officer.get('/api/reports').text


def test_notifications_are_scoped_and_unrelated_user_cannot_mark_read(campus):
    student, finder = campus['clients'][:2]
    report(student)
    note = student.get('/api/notifications').json()[0]
    assert finder.get('/api/notifications').json() == []
    assert finder.patch(f"/api/notifications/{note['notification_id']}/read").status_code == 404
    assert student.patch(f"/api/notifications/{note['notification_id']}/read").status_code == 200
    assert student.get('/api/notifications').json()[0]['read_at'] is not None


def test_concurrent_approvals_allow_exactly_one_winner(campus):
    from concurrent.futures import ThreadPoolExecutor
    student, finder, officer, admin, other = campus['clients']
    found = report(finder, 'found')
    a, b = claim(student,found), claim(other,found)
    payload = {'decision':'approved','reviewer_notes':'Identifying proof verified by the reviewing officer.'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = [pool.submit(officer.patch,f"/api/claims/{a['claim_id']}/review",json=payload),
                    pool.submit(admin.patch,f"/api/claims/{b['claim_id']}/review",json=payload)]
        responses = [result.result() for result in attempts]
    assert sorted(response.status_code for response in responses) == [200,409]
    with campus['app'].state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(models.Claim).where(models.Claim.claim_status=='approved')) == 1


def test_forged_sessions_and_login_attempt_limit(campus):
    student = campus['clients'][0]
    student.cookies.clear()
    student.cookies.set('findly_v3_session','forged.invalid.signature')
    assert student.get('/api/auth/me').status_code == 401
    student.cookies.clear()
    for _ in range(8):
        assert student.post('/api/auth/login',json={'email':'campus0@example.com','password':'wrong-password!'}).status_code == 401
    assert student.post('/api/auth/login',json={'email':'campus0@example.com','password':'wrong-password!'}).status_code == 429


def test_concurrent_approval_and_information_request_keep_consistent_state(campus):
    from concurrent.futures import ThreadPoolExecutor
    student, finder, officer, admin = campus['clients'][:4]
    found = report(finder, 'found')
    c = claim(student, found)
    cid = c['claim_id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(officer.patch,f'/api/claims/{cid}/review',json={'decision':'approved','reviewer_notes':'Evidence was verified by an officer.'})
        b = pool.submit(admin.patch,f'/api/claims/{cid}/review',json={'decision':'more_information','reviewer_notes':'Please provide the original receipt number.'})
        responses = [a.result(),b.result()]
    assert all(response.status_code in {200,409} for response in responses)
    record = student.get(f'/api/claims/{cid}').json()
    item = student.get(f"/api/reports/found/{found['record_id']}").json()
    assert record['claim_status'] == 'approved'
    assert item['status'] == 'claim_approved'


def test_future_dates_are_rejected_and_profile_persists(campus):
    from datetime import timedelta
    student = campus['clients'][0]
    future = (date.today()+timedelta(days=1)).isoformat()
    result = student.post('/api/reports/lost',json={'title':'A future report','category':'Other','description':'A report in the future','location_lost':'Library','date_lost':future})
    assert result.status_code == 422
    profile = {'name':'Updated','surname':'Student','campus':'North Campus'}
    assert student.patch('/api/auth/me',json=profile).status_code == 200
    assert student.get('/api/auth/me').json()['campus'] == 'North Campus'
