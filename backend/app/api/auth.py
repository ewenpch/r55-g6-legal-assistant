"""Inscription, connexion, déconnexion. Mots de passe hachés avec bcrypt ; session par cookie."""

import hashlib
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, field_validator

from app.config import Settings, get_settings
from app.db import Db

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "session"
SESSION_DAYS = 7
MIN_PASSWORD = 8
MAX_PASSWORD_BYTES = 72  # limite de bcrypt
# Hash factice : évite de révéler par le temps de réponse si un e-mail existe.
_DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt())


class Credentials(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        value = value.strip().lower()
        local, _, domain = value.partition("@")
        if not local or "." not in domain or " " in value or len(value) > 254:
            raise ValueError("Adresse e-mail invalide.")
        return value


class RegisterRequest(Credentials):
    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        if len(value) < MIN_PASSWORD:
            raise ValueError(f"Le mot de passe doit faire au moins {MIN_PASSWORD} caractères.")
        if len(value.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError("Le mot de passe est trop long (72 octets maximum).")
        return value


class User(BaseModel):
    id: int
    email: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _start_session(db: sqlite3.Connection, response: Response, settings: Settings, user_id: int):
    token = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(days=SESSION_DAYS)
    db.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_hash_token(token), user_id, expires.isoformat()),
    )
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def current_user(db: Db, session: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None) -> User:
    """Dépendance des routes protégées : 401 si non connecté."""
    if session:
        row = db.execute(
            "SELECT u.id, u.email, s.expires_at FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token_hash = ?",
            (_hash_token(session),),
        ).fetchone()
        if row and datetime.fromisoformat(row["expires_at"]) > datetime.now(UTC):
            return User(id=row["id"], email=row["email"])
    raise HTTPException(status_code=401, detail="Connexion requise.")


CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/register", status_code=201)
def register(
    body: RegisterRequest,
    response: Response,
    db: Db,
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    try:
        cursor = db.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)", (body.email, password_hash)
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409, detail="Un compte existe déjà avec cet e-mail."
        ) from None
    _start_session(db, response, settings, cursor.lastrowid)
    return User(id=cursor.lastrowid, email=body.email)


@router.post("/login")
def login(
    body: Credentials,
    response: Response,
    db: Db,
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    row = db.execute(
        "SELECT id, email, password_hash FROM users WHERE email = ?", (body.email,)
    ).fetchone()
    stored = row["password_hash"].encode() if row else _DUMMY_HASH
    try:
        valid = bcrypt.checkpw(body.password.encode()[:MAX_PASSWORD_BYTES], stored)
    except ValueError:
        valid = False
    if not row or not valid:
        raise HTTPException(status_code=401, detail="E-mail ou mot de passe incorrect.")
    _start_session(db, response, settings, row["id"])
    return User(id=row["id"], email=row["email"])


@router.post("/logout", status_code=204)
def logout(
    response: Response, db: Db, session: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None
) -> None:
    if session:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(session),))
    response.delete_cookie(COOKIE_NAME)


@router.get("/me")
def me(user: CurrentUser) -> User:
    return user
