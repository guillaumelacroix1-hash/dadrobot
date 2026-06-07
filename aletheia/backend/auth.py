"""Accès protégé par mot de passe unique + jeton de session signé."""
from __future__ import annotations

from fastapi import HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from . import config

_serializer = URLSafeTimedSerializer(config.SECRET_KEY, salt="aletheia-session")
MAX_AGE = 60 * 60 * 24 * 30  # 30 jours
COOKIE = "aletheia_session"


def check_password(password: str) -> bool:
    # Si aucun mot de passe n'est configuré, l'accès est ouvert (mode dev local).
    if not config.APP_PASSWORD:
        return True
    return password == config.APP_PASSWORD


def make_token() -> str:
    return _serializer.dumps({"ok": True})


def valid_token(token: str | None) -> bool:
    if not config.APP_PASSWORD:
        return True
    if not token:
        return False
    try:
        _serializer.loads(token, max_age=MAX_AGE)
        return True
    except BadSignature:
        return False


def require_auth(request: Request) -> None:
    """Dépendance FastAPI : protège une route."""
    token = request.cookies.get(COOKIE) or request.headers.get("X-Auth-Token")
    if not valid_token(token):
        raise HTTPException(status_code=401, detail="Authentification requise")
