import os
import jwt

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, insert
from werkzeug.security import check_password_hash, generate_password_hash
from database.database import engine, users
from datetime import datetime, timezone, timedelta
from schemas.schemas import UserCreate, UserLogin, UserOut, TokenOut
from typing import List

import events

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

users_router = APIRouter()
bearer = HTTPBearer()


def create_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        return jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido.")


@users_router.post("/api/users/register", response_model=UserOut, status_code=201)
def register(body: UserCreate):
    with engine.connect() as conn:
        existing = conn.execute(select(users).where(users.c.email == body.email)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="El correo ya está registrado.")

        result = conn.execute(
            insert(users).values(
                full_name=body.full_name,
                email=body.email,
                password_hash=generate_password_hash(body.password),
                role=body.role,
                created_at=datetime.now(timezone.utc),
            )
        )
        conn.commit()
        user = conn.execute(select(users).where(users.c.id == result.inserted_primary_key[0])).fetchone()
        user_out = UserOut(**dict(zip(users.c.keys(), user)))

    events.publish("user.created", user_out.model_dump(mode="json"))
    return user_out


@users_router.post("/api/users/login", response_model=TokenOut)
def login(body: UserLogin):
    with engine.connect() as conn:
        user = conn.execute(select(users).where(users.c.email == body.email)).fetchone()

    if user is None or not check_password_hash(user.password_hash, body.password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas.")

    return TokenOut(access_token=create_token(user.id, user.role))


@users_router.get("/api/users", response_model=List[UserOut])
def list_users(token: dict = Depends(decode_token)):
    if token["role"] != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    with engine.connect() as conn:
        result = conn.execute(select(users).order_by(users.c.created_at.desc()))
        return [UserOut(**dict(zip(users.c.keys(), row))) for row in result]


@users_router.get("/api/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, token: dict = Depends(decode_token)):
    with engine.connect() as conn:
        user = conn.execute(select(users).where(users.c.id == user_id)).fetchone()

    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    return UserOut(**dict(zip(users.c.keys(), user)))
