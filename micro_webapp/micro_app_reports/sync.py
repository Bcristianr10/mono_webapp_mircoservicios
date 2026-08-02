import os
from datetime import datetime, timezone, timedelta

import httpx
import jwt

import upsert

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"

USERS_URL = os.getenv("USERS_URL", "http://micro_app_user:8001")
COURSES_URL = os.getenv("COURSES_URL", "http://micro_app_courses:8002")
ENROLLMENTS_URL = os.getenv("ENROLLMENTS_URL", "http://micro_app_enrollments:8003")

TIMEOUT = 10


def _service_token() -> str:
    """Token interno servicio-a-servicio, no ligado a un usuario real."""
    payload = {
        "sub": "0",
        "role": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def refresh() -> None:
    """Reconciliacion: trae el estado actual de users/courses/enrollments y hace
    UPSERT (no borra nada) para no perder el historial acumulado por eventos.
    Ningun servicio real borra usuarios/cursos/matriculas (solo las desactiva o
    cancela), asi que UPSERT es suficiente, no hace falta borrar filas viejas."""
    headers = {"Authorization": f"Bearer {_service_token()}"}

    users_data = httpx.get(f"{USERS_URL}/api/users", headers=headers, timeout=TIMEOUT).json()
    courses_data = httpx.get(f"{COURSES_URL}/api/courses/all", headers=headers, timeout=TIMEOUT).json()
    enrollments_data = httpx.get(
        f"{ENROLLMENTS_URL}/api/enrollments/all", headers=headers, timeout=TIMEOUT
    ).json()

    for row in users_data:
        upsert.upsert_user(row)
    for row in courses_data:
        upsert.upsert_course(row)
    for row in enrollments_data:
        upsert.upsert_enrollment(row)
