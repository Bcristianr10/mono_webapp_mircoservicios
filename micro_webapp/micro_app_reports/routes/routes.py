import os

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import logic
import sync
from database.database import engine

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"

reports_router = APIRouter()
bearer = HTTPBearer()


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        return jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido.")


@reports_router.get("/api/reports/health")
def health():
    with engine.connect():
        pass
    return {"status": "ok"}


@reports_router.post("/api/reports/sync")
def manual_sync(token: dict = Depends(decode_token)):
    """Reconciliacion manual: red de seguridad si algun evento se perdio.
    El worker (worker.py) es quien mantiene la copia al dia en el uso normal."""
    if token["role"] != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    sync.refresh()
    return {"status": "synced"}


@reports_router.get("/api/reports/dashboard")
def dashboard(token: dict = Depends(decode_token)):
    if token["role"] != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    # Ya no se sincroniza aqui: el worker mantiene la copia al dia via eventos.
    stats = logic.course_enrollment_stats()

    return {
        "kpis": logic.get_kpis(),
        "top_courses": logic.top_courses(stats),
        "at_risk_courses": logic.courses_at_risk(stats),
        "instructor_workload": logic.instructor_workload(stats),
        "top_students": logic.top_students(),
        "inactive_students": logic.students_without_enrollments(),
        "monthly_trend": logic.monthly_enrollment_trend(),
        "cancellation_report": logic.cancellation_rate_by_course(),
        "cancellations_trend": logic.cancellations_per_month(),
        "time_to_cancel": logic.avg_days_to_cancellation_by_course(),
    }
