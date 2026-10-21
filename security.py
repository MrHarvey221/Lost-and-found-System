"""Password hashing, signed HttpOnly sessions, and server-enforced roles."""
from collections import defaultdict, deque
from hashlib import pbkdf2_hmac
import hmac
import secrets
from time import monotonic
from fastapi import Depends, HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session
from database import get_db
from models import User

COOKIE = 'findly_v3_session'
REVIEW_ROLES = {'security', 'lost_property', 'administrator'}


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 600_000).hex()
    return f'pbkdf2_sha256$600000${salt}${digest}'


def verify_password(password, stored):
    try:
        algorithm, rounds, salt, expected = stored.split('$')
        if algorithm == 'legacy_pbkdf2_sha256' and int(rounds) == 310000:
            actual = pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 310000).hex()
            return hmac.compare_digest(actual, expected)
        if algorithm != 'pbkdf2_sha256' or int(rounds) != 600_000:
            return False
        actual = pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, AttributeError):
        return False


DUMMY_HASH = hash_password(secrets.token_urlsafe(24))


def serializer(request):
    return URLSafeTimedSerializer(request.app.state.settings.session_secret, salt='findly-session-v1')


def set_session(request, response, user):
    settings = request.app.state.settings
    token = serializer(request).dumps({'uid': user.user_id, 'v': user.auth_version})
    response.set_cookie(COOKIE, token, max_age=settings.session_hours * 3600,
                        httponly=True, secure=settings.cookie_secure, samesite='strict', path='/')


def current_user(request: Request, db: Session = Depends(get_db)):
    try:
        token = request.cookies.get(COOKIE, '')
        payload = serializer(request).loads(token, max_age=request.app.state.settings.session_hours * 3600)
        user = db.get(User, int(payload['uid']))
        if not user or user.account_status != 'active' or user.auth_version != payload['v']:
            raise ValueError('Session revoked')
        return user
    except (BadSignature, SignatureExpired, ValueError, KeyError, TypeError):
        raise HTTPException(401, 'Please log in to continue.')


def reviewer(user: User = Depends(current_user)):
    if user.role not in REVIEW_ROLES:
        raise HTTPException(403, 'An authorized officer or administrator is required.')
    return user


def administrator(user: User = Depends(current_user)):
    if user.role != 'administrator':
        raise HTTPException(403, 'Administrator access is required.')
    return user


class LoginLimiter:
    """Local, single-process attempt limiting; not a distributed rate limiter."""
    def __init__(self):
        self.attempts = defaultdict(deque)

    def check(self, ip, email):
        now = monotonic()
        # Prune idle keys so repeated random emails do not grow memory forever.
        for key in list(self.attempts):
            queue = self.attempts[key]
            while queue and queue[0] < now - 900:
                queue.popleft()
            if not queue:
                del self.attempts[key]
        for key, limit in ((ip, 40), ((ip, email), 8)):
            if len(self.attempts[key]) >= limit:
                raise HTTPException(429, 'Too many login attempts. Try again in 15 minutes.')

    def failure(self, ip, email):
        now = monotonic()
        self.attempts[ip].append(now)
        self.attempts[(ip, email)].append(now)
