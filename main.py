"""Findly FastAPI application, serving the original frontend and authenticated API."""
from contextlib import asynccontextmanager
import json
from typing import Literal
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import crud
import models
import schemas
from config import ROOT, Settings
from database import get_db, make_engine, session_factory
from matching import MatchEngine, refresh_matches
from data_migration import migrate_inline_photos
from migration_safety import upgrade_database
from security import COOKIE, DUMMY_HASH, REVIEW_ROLES, LoginLimiter, administrator, current_user, hash_password, reviewer, set_session, verify_password
from uploads import store_upload, upload_path
from views import claim_view, evidence_view, match_view, notification_view, report_view, timestamp, user_view

Kind = Literal['lost', 'found']


def documented_request_header(x_findly_request: str = Header('1', alias='X-Findly-Request')):
    """Expose the middleware-enforced write header in interactive API docs."""
    return x_findly_request


def get_report(db, kind, report_id):
    item = db.get(models.LostItem if kind == 'lost' else models.FoundItem, report_id)
    if not item:
        raise HTTPException(404, 'Report not found.')
    return item


def create_app(settings=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.settings = (settings or Settings.from_env()).prepare()
        app.state.engine = make_engine(app.state.settings.database_url)
        upgrade_database(app.state.engine)
        app.state.sessions = session_factory(app.state.engine)
        app.state.limiter = LoginLimiter()
        await migrate_inline_photos(app.state.sessions,app.state.settings.data_dir)
        app.state.matcher = MatchEngine(app.state.settings.semantic_mode,app.state.settings.semantic_model_dir)
        with app.state.sessions() as db:
            refresh_matches(db,app.state.settings.match_threshold,app.state.matcher)
            db.commit()
        try:
            yield
        finally:
            app.state.engine.dispose()

    app = FastAPI(title='Findly Campus Lost and Found', version='3.0.0', lifespan=lifespan,
                  dependencies=[Depends(documented_request_header)],
                  description='Use the served frontend. API writes require X-Findly-Request: 1 and an authenticated session where applicable.')
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost','127.0.0.1','testserver'])

    @app.middleware('http')
    async def browser_security(request, call_next):
        if request.method in {'POST','PUT','PATCH','DELETE'} and request.url.path.startswith('/api/'):
            origin = request.headers.get('origin')
            expected = f'{request.url.scheme}://{request.url.netloc}'
            if request.headers.get('x-findly-request') != '1' or (origin and origin.rstrip('/') != expected):
                return JSONResponse({'detail':'Invalid request origin or missing X-Findly-Request header.'}, status_code=403)
            try:
                limit = 13 * 1024 * 1024 if request.url.path.endswith('/photos') else 4 * 1024 * 1024
                if int(request.headers.get('content-length', '0')) > limit:
                    return JSONResponse({'detail':'Request is too large.'}, status_code=413)
            except ValueError:
                return JSONResponse({'detail':'Invalid Content-Length.'}, status_code=400)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        if request.url.path not in {'/docs','/redoc','/docs/oauth2-redirect'}:
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' blob: data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response

    @app.exception_handler(IntegrityError)
    async def integrity_error(request, exc):
        return JSONResponse({'detail':'This operation conflicts with an existing record. Refresh and try again.'}, status_code=409)

    @app.get('/', include_in_schema=False)
    def index():
        return FileResponse(ROOT / 'index.html', headers={'Cache-Control':'no-store'})

    @app.get('/app.js', include_in_schema=False)
    def javascript():
        return FileResponse(ROOT / 'app.js', media_type='text/javascript', headers={'Cache-Control':'no-cache'})

    @app.get('/styles.css', include_in_schema=False)
    def stylesheet():
        return FileResponse(ROOT / 'styles.css', media_type='text/css')

    @app.get('/api/health')
    def health(db: Session = Depends(get_db)):
        db.execute(select(1))
        return {'status':'ok', 'version':'3.0.0'}

    @app.get('/api/config')
    def public_config(request: Request):
        return {'demo_mode':request.app.state.settings.demo_mode,'version':'3.0.0'}

    @app.get('/api/matching/status')
    def matching_status(request: Request, user: models.User = Depends(current_user)):
        return {**request.app.state.matcher.status(),'threshold':request.app.state.settings.match_threshold}

    @app.post('/api/auth/register', status_code=201, response_model=schemas.UserOut)
    def register(data: schemas.UserCreate, request: Request, response: Response, db: Session = Depends(get_db)):
        email = str(data.email).lower()
        if db.scalar(select(models.User).where(func.lower(models.User.email) == email)):
            raise HTTPException(409, 'An account already uses that email.')
        values = data.model_dump(exclude={'password','email'})
        user = models.User(**values, email=email, password_hash=hash_password(data.password), account_status='active')
        db.add(user)
        db.flush()
        crud.history(db, 'user', user.user_id, None, 'active', user.user_id, 'Self-registration')
        db.commit()
        set_session(request, response, user)
        return user_view(user)

    @app.post('/api/auth/login', response_model=schemas.UserOut)
    def login(data: schemas.Login, request: Request, response: Response, db: Session = Depends(get_db)):
        email = str(data.email).lower()
        ip = request.client.host if request.client else 'local'
        request.app.state.limiter.check(ip, email)
        user = db.scalar(select(models.User).where(func.lower(models.User.email) == email))
        valid = verify_password(data.password, user.password_hash if user and user.password_hash else DUMMY_HASH)
        if not user or not valid or user.account_status != 'active' or not user.password_hash:
            request.app.state.limiter.failure(ip, email)
            raise HTTPException(401, 'Incorrect email or password, or account unavailable.')
        if user.password_hash.startswith('legacy_'):
            user.password_hash=hash_password(data.password)
            db.commit()
        set_session(request, response, user)
        return user_view(user)

    @app.get('/api/auth/me', response_model=schemas.UserOut)
    def me(user: models.User = Depends(current_user)):
        return user_view(user)

    @app.patch('/api/auth/me', response_model=schemas.UserOut)
    def update_profile(data: schemas.ProfileUpdate, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        for key, value in data.model_dump().items():
            setattr(user, key, value)
        crud.history(db, 'user', user.user_id, 'active', 'active', user.user_id, 'Profile updated')
        db.commit()
        return user_view(user)

    @app.post('/api/auth/logout', status_code=204)
    def logout(response: Response, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        user.auth_version += 1
        db.commit()
        response.delete_cookie(COOKIE, path='/')

    @app.get('/api/reports', response_model=list[schemas.ReportOut], response_model_exclude_unset=True)
    def reports(q: str = Query('', max_length=150), kind: Kind | None = None,
                category: str | None = None, mine: bool = False,
                db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        results = []
        for label, cls in [('lost', models.LostItem), ('found', models.FoundItem)]:
            if kind and kind != label:
                continue
            statement = select(cls)
            if mine:
                statement = statement.where(cls.reporter_id == user.user_id)
            if category:
                statement = statement.where(cls.category == category)
            if q:
                location = cls.location_lost if label == 'lost' else cls.location_found
                statement = statement.where(or_(*[column.contains(q, autoescape=True) for column in
                    (cls.title, cls.description, cls.category, cls.colour, cls.brand, location)]))
            results.extend(report_view(item, user) for item in db.scalars(statement).all())
        return sorted(results, key=lambda row: row['created_at'] or '', reverse=True)

    @app.post('/api/reports/lost', status_code=201, response_model=schemas.ReportOut, response_model_exclude_unset=True)
    def report_lost(data: schemas.LostItemCreate, request: Request, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        item = crud.create_report(db, data, user, 'lost', request.app.state.settings.match_threshold, request.app.state.matcher)
        db.commit()
        return report_view(item, user)

    @app.post('/api/reports/found', status_code=201, response_model=schemas.ReportOut, response_model_exclude_unset=True)
    def report_found(data: schemas.FoundItemCreate, request: Request, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        item = crud.create_report(db, data, user, 'found', request.app.state.settings.match_threshold, request.app.state.matcher)
        db.commit()
        return report_view(item, user)

    @app.get('/api/reports/{kind}/{report_id}', response_model=schemas.ReportOut, response_model_exclude_unset=True)
    def report_detail(kind: Kind, report_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        return report_view(get_report(db, kind, report_id), user)

    @app.patch('/api/reports/{kind}/{report_id}/status')
    def report_status(kind: Kind, report_id: int, data: schemas.StatusUpdate, request: Request,
                      db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        item = crud.update_report_status(db, get_report(db, kind, report_id), kind, data, user,
                                        request.app.state.settings.match_threshold, request.app.state.matcher)
        db.commit()
        return report_view(item, user)

    @app.patch('/api/reports/found/{report_id}/storage', response_model=schemas.ReportOut, response_model_exclude_unset=True)
    def report_storage(report_id: int, data: schemas.StorageUpdate,
                       db: Session = Depends(get_db), user: models.User = Depends(reviewer)):
        item = get_report(db, 'found', report_id)
        item.storage_location = data.storage_location
        crud.history(db, 'found', report_id, item.status, item.status, user.user_id, 'Internal storage updated: ' + data.reason)
        db.commit()
        return report_view(item, user)

    @app.post('/api/reports/{kind}/{report_id}/image', status_code=201)
    async def report_image(kind: Kind, report_id: int, request: Request, file: UploadFile = File(...),
                           db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        item = get_report(db, kind, report_id)
        if item.reporter_id != user.user_id and user.role not in REVIEW_ROLES:
            raise HTTPException(403, 'You cannot change this report image.')
        name = await store_upload(file, request.app.state.settings.data_dir / 'report_images')
        item.image_ref = name
        item.image_refs = json.dumps([name])
        crud.history(db, kind, report_id, item.status, item.status, user.user_id, 'Report photograph uploaded')
        db.commit()
        return report_view(item, user)

    @app.get('/api/reports/{kind}/{report_id}/image')
    def get_report_image(kind: Kind, report_id: int, request: Request, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        item = get_report(db, kind, report_id)
        if request.app.state.settings.demo_mode and item.image_ref and item.image_ref.startswith('demo:'):
            name=item.image_ref.removeprefix('demo:')
            if name in {'bottle','bag','phone','keys','sleeve'}:
                return FileResponse(ROOT/'demo-assets'/(name+'.svg'),media_type='image/svg+xml')
        return FileResponse(upload_path(request.app.state.settings.data_dir / 'report_images', item.image_ref), media_type='image/jpeg')

    @app.post('/api/reports/{kind}/{report_id}/photos', status_code=201)
    async def report_photos(kind: Kind, report_id: int, request: Request, files: list[UploadFile] = File(...),
                            db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        item=get_report(db,kind,report_id)
        if item.reporter_id!=user.user_id and user.role not in REVIEW_ROLES:
            raise HTTPException(403,'You cannot change these photographs.')
        if not 1<=len(files)<=4 or (kind=='lost' and len(files)>1):
            raise HTTPException(422,'Choose one lost-item photo, or up to four found-item photos.')
        names=[]
        try:
            for file in files:names.append(await store_upload(file,request.app.state.settings.data_dir/'report_images'))
        except Exception:
            # Remove only files created by this failed upload, never previous photos.
            for name in names:(request.app.state.settings.data_dir/'report_images'/name).unlink(missing_ok=True)
            raise
        item.image_refs=json.dumps(names);item.image_ref=names[0]
        crud.history(db,kind,report_id,item.status,item.status,user.user_id,'Report photographs uploaded')
        db.commit()
        return report_view(item,user)

    @app.get('/api/reports/{kind}/{report_id}/photos/{index}')
    def report_photo(kind: Kind, report_id: int, index: int, request: Request,
                     db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        item=get_report(db,kind,report_id)
        try:refs=json.loads(item.image_refs or '[]')
        except ValueError:refs=[]
        if index<0 or index>=len(refs):raise HTTPException(404,'Photograph not found.')
        return FileResponse(upload_path(request.app.state.settings.data_dir/'report_images',refs[index]),media_type='image/jpeg')

    @app.get('/api/matches', response_model=list[schemas.MatchOut], response_model_exclude_unset=True)
    def matches(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        query = select(models.Match).where(models.Match.match_status == 'candidate').order_by(models.Match.similarity_score.desc())
        if user.role not in REVIEW_ROLES:
            query = query.join(models.LostItem).join(models.FoundItem).where(or_(
                models.LostItem.reporter_id == user.user_id, models.FoundItem.reporter_id == user.user_id))
        return [match_view(match, user) for match in db.scalars(query).all()]

    @app.post('/api/matches/recheck')
    def recheck(request: Request, db: Session = Depends(get_db), user: models.User = Depends(reviewer)):
        refresh_matches(db, request.app.state.settings.match_threshold, request.app.state.matcher)
        db.commit()
        return {'message':'Open reports were rechecked.'}

    @app.get('/api/matches/{match_id}', response_model=schemas.MatchOut, response_model_exclude_unset=True)
    def match_detail(match_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        match=db.get(models.Match,match_id)
        if not match or (user.role not in REVIEW_ROLES and user.user_id not in {match.lost_item.reporter_id,match.found_item.reporter_id}):
            raise HTTPException(404,'Match not found.')
        return match_view(match,user)

    @app.post('/api/claims', status_code=201, response_model=schemas.ClaimOut, response_model_exclude_unset=True)
    def claim_create(data: schemas.ClaimCreate, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        claim = crud.create_claim(db, data, user)
        db.commit()
        return claim_view(claim, user, details=True)

    @app.get('/api/claims', response_model=list[schemas.ClaimOut], response_model_exclude_unset=True)
    def claims(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        query = select(models.Claim).order_by(models.Claim.claim_id.desc())
        if user.role not in REVIEW_ROLES:
            query = query.where(models.Claim.claimant_id == user.user_id)
        return [claim_view(claim, user) for claim in db.scalars(query).all()]

    @app.get('/api/claims/{claim_id}', response_model=schemas.ClaimOut, response_model_exclude_unset=True)
    def claim_detail(claim_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        return claim_view(crud.authorized_claim(db, claim_id, user), user, details=True)

    @app.patch('/api/claims/{claim_id}/review')
    def claim_review(claim_id: int, data: schemas.ClaimReviewUpdate, request: Request,
                     db: Session = Depends(get_db), user: models.User = Depends(reviewer)):
        claim = crud.authorized_claim(db, claim_id, user)
        crud.review_claim(db, claim, data, user, request.app.state.settings.match_threshold, request.app.state.matcher)
        db.commit()
        return claim_view(claim, user, details=True)

    @app.post('/api/claims/{claim_id}/evidence', status_code=201)
    async def claim_evidence(claim_id: int, request: Request,
            private_description: str = Form(..., min_length=8, max_length=2000),
            file: UploadFile | None = File(None), db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        claim = crud.authorized_claim(db, claim_id, user)
        if claim.claimant_id != user.user_id:
            raise HTTPException(403, 'Only the claimant may submit ownership evidence.')
        if claim.claim_status not in crud.ACTIVE_CLAIMS:
            raise HTTPException(409, 'Evidence is closed for a decided claim.')
        description = private_description.strip()
        if len(description) < 8:
            raise HTTPException(422, 'Provide at least eight characters of ownership detail.')
        name = await store_upload(file, request.app.state.settings.data_dir / 'evidence', evidence=True) if file else None
        evidence = models.ClaimEvidence(claim_id=claim_id, evidence_type='document' if name else 'ownership_detail',
                                       private_description=description, uploaded_proof_ref=name)
        db.add(evidence)
        previous = claim.claim_status
        claim.claim_status = 'submitted'
        crud.history(db, 'claim', claim_id, previous, 'submitted', user.user_id, 'Additional private evidence submitted')
        crud.notify_officers(db, 'claim', f'Claim #{claim_id} has additional evidence.', exclude=user.user_id)
        db.commit()
        return evidence_view(evidence)

    @app.get('/api/evidence/{evidence_id}/file')
    def evidence_file(evidence_id: int, request: Request, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        evidence = db.get(models.ClaimEvidence, evidence_id)
        if not evidence:
            raise HTTPException(404, 'Evidence not found.')
        crud.authorized_claim(db, evidence.claim_id, user)
        path = upload_path(request.app.state.settings.data_dir / 'evidence', evidence.uploaded_proof_ref)
        return FileResponse(path, filename=f'claim-{evidence.claim_id}-proof{path.suffix}',
                            media_type='application/pdf' if path.suffix == '.pdf' else 'image/jpeg')

    @app.get('/api/notifications', response_model=list[schemas.NotificationOut])
    def notifications(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        query = select(models.Notification).where(models.Notification.recipient_id == user.user_id).order_by(models.Notification.notification_id.desc())
        return [notification_view(n) for n in db.scalars(query).all()]

    @app.patch('/api/notifications/read-all')
    def read_all(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        for note in db.scalars(select(models.Notification).where(models.Notification.recipient_id == user.user_id, models.Notification.read_at.is_(None))).all():
            note.read_at = models.utcnow()
        db.commit()
        return {'message':'All notifications marked as read.'}

    @app.patch('/api/notifications/{notification_id}/read')
    def read_note(notification_id: int, db: Session = Depends(get_db), user: models.User = Depends(current_user)):
        note = db.get(models.Notification, notification_id)
        if not note or note.recipient_id != user.user_id:
            raise HTTPException(404, 'Notification not found.')
        note.read_at = note.read_at or models.utcnow()
        db.commit()
        return notification_view(note)

    @app.get('/api/admin/users')
    def users(db: Session = Depends(get_db), user: models.User = Depends(administrator)):
        return [user_view(row) for row in db.scalars(select(models.User).order_by(models.User.user_id)).all()]

    @app.patch('/api/admin/users/{user_id}')
    def manage_user(user_id: int, data: schemas.UserAdminUpdate, db: Session = Depends(get_db), user: models.User = Depends(administrator)):
        target = db.get(models.User, user_id)
        if not target:
            raise HTTPException(404, 'User not found.')
        if target.user_id == user.user_id:
            raise HTTPException(409, 'Use another administrator to change your own access.')
        previous = f'{target.role}:{target.account_status}'
        target.role, target.account_status = data.role, data.account_status
        target.auth_version += 1
        crud.history(db, 'user', target.user_id, previous, f'{data.role}:{data.account_status}', user.user_id, data.reason)
        crud.notify(db, target.user_id, 'account', f'Your account is now {data.account_status}, with role {data.role}.')
        db.commit()
        return user_view(target)

    @app.get('/api/admin/history')
    def audit_history(db: Session = Depends(get_db), user: models.User = Depends(administrator)):
        rows = db.scalars(select(models.StatusHistory).order_by(models.StatusHistory.history_id.desc())).all()
        return [dict(history_id=row.history_id, related_record_type=row.related_record_type,
            related_record_id=row.related_record_id, previous_status=row.previous_status, new_status=row.new_status,
            actor_id=row.actor_id, timestamp=timestamp(row.timestamp), reason=row.reason) for row in rows]

    return app


app = create_app()
