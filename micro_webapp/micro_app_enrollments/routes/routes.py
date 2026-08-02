import os
import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func, insert, select, update
from datetime import datetime, timezone
from typing import List
from database.database import engine, enrollments, enrollment_status_history
from schemas.schemas import EnrollmentCreate, EnrollmentOut

import events

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
COURSES_URL = os.getenv("COURSES_URL", "http://micro_app_courses:8002")

enrollments_router = APIRouter()
bearer = HTTPBearer()


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        return jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido.")


def get_course(course_id: int, token: str) -> dict:
    resp = httpx.get(
        f"{COURSES_URL}/api/courses/{course_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Curso no encontrado.")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Error al consultar el servicio de cursos.")
    return resp.json()


@enrollments_router.get("/api/enrollments", response_model=List[EnrollmentOut])
def my_enrollments(token: dict = Depends(decode_token)):
    user_id = int(token["sub"])
    with engine.connect() as conn:
        result = conn.execute(
            select(enrollments)
            .where(enrollments.c.user_id == user_id, enrollments.c.status == "active")
        )
        return [EnrollmentOut(**dict(zip(enrollments.c.keys(), row))) for row in result]


@enrollments_router.get("/api/enrollments/all", response_model=List[EnrollmentOut])
def list_all_enrollments(token: dict = Depends(decode_token)):
    if token["role"] != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    with engine.connect() as conn:
        result = conn.execute(select(enrollments))
        return [EnrollmentOut(**dict(zip(enrollments.c.keys(), row))) for row in result]


@enrollments_router.post("/api/enrollments", response_model=EnrollmentOut, status_code=201)
def enroll(body: EnrollmentCreate, credentials: HTTPAuthorizationCredentials = Depends(bearer), token: dict = Depends(decode_token)):
    user_id = int(token["sub"])
    course = get_course(body.course_id, credentials.credentials)

    if not course["is_active"]:
        raise HTTPException(status_code=400, detail="El curso no está activo.")

    with engine.connect() as conn:
        existing = conn.execute(
            select(enrollments).where(
                enrollments.c.user_id == user_id,
                enrollments.c.course_id == body.course_id,
            )
        ).fetchone()

        if existing and existing.status == "active":
            raise HTTPException(status_code=409, detail="Ya estás inscrito en este curso.")

        enrolled_count = conn.execute(
            select(func.count(enrollments.c.id)).where(
                enrollments.c.course_id == body.course_id,
                enrollments.c.status == "active",
            )
        ).scalar()

        if enrolled_count >= course["capacity"]:
            raise HTTPException(status_code=409, detail="El curso ya alcanzó su cupo máximo.")

        changed_at = datetime.now(timezone.utc)

        if existing:
            conn.execute(
                update(enrollments)
                .where(enrollments.c.id == existing.id)
                .values(status="active", enrolled_at=changed_at)
            )
            enrollment_id = existing.id
        else:
            result = conn.execute(
                insert(enrollments).values(
                    user_id=user_id,
                    course_id=body.course_id,
                    status="active",
                    enrolled_at=changed_at,
                )
            )
            enrollment_id = result.inserted_primary_key[0]

        conn.execute(
            insert(enrollment_status_history).values(
                enrollment_id=enrollment_id, status="active", changed_at=changed_at
            )
        )
        conn.commit()
        row = conn.execute(select(enrollments).where(enrollments.c.id == enrollment_id)).fetchone()
        enrollment_out = EnrollmentOut(**dict(zip(enrollments.c.keys(), row)))

    events.publish("enrollment.created", enrollment_out.model_dump(mode="json"))
    events.publish(
        "enrollment.status_changed",
        {"enrollment_id": enrollment_id, "status": "active", "changed_at": changed_at},
    )
    return enrollment_out


@enrollments_router.get("/api/enrollments/course/{course_id}", response_model=List[EnrollmentOut])
def enrollments_for_course(course_id: int, token: dict = Depends(decode_token)):
    if token["role"] not in ("instructor", "admin"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    with engine.connect() as conn:
        result = conn.execute(
            select(enrollments).where(
                enrollments.c.course_id == course_id,
                enrollments.c.status == "active",
            )
        )
        return [EnrollmentOut(**dict(zip(enrollments.c.keys(), row))) for row in result]


@enrollments_router.get("/api/enrollments/course/{course_id}/count")
def count_for_course(course_id: int, token: dict = Depends(decode_token)):
    with engine.connect() as conn:
        count = conn.execute(
            select(func.count(enrollments.c.id)).where(
                enrollments.c.course_id == course_id,
                enrollments.c.status == "active",
            )
        ).scalar()
    return {"course_id": course_id, "count": count}

@enrollments_router.delete("/api/enrollments/{course_id}", status_code=204)
def cancel_enrollment(course_id: int, token: dict = Depends(decode_token)):
    user_id = int(token["sub"])

    with engine.connect() as conn:
        existing = conn.execute(
            select(enrollments).where(
                enrollments.c.user_id == user_id,
                enrollments.c.course_id == course_id,
                enrollments.c.status == "active",
            )
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail="No existe una matrícula activa para cancelar.")

        changed_at = datetime.now(timezone.utc)
        conn.execute(
            update(enrollments)
            .where(enrollments.c.id == existing.id)
            .values(status="cancelled")
        )
        conn.execute(
            insert(enrollment_status_history).values(
                enrollment_id=existing.id, status="cancelled", changed_at=changed_at
            )
        )
        conn.commit()

    events.publish(
        "enrollment.cancelled",
        {
            "id": existing.id,
            "user_id": existing.user_id,
            "course_id": existing.course_id,
            "status": "cancelled",
            "enrolled_at": existing.enrolled_at,
        },
    )
    events.publish(
        "enrollment.status_changed",
        {"enrollment_id": existing.id, "status": "cancelled", "changed_at": changed_at},
    )

@enrollments_router.delete("/api/enrollments/course/{course_id}/all", status_code=204)
def cancel_all_for_course(course_id: int, token: dict = Depends(decode_token)):
    if token["role"] not in ("instructor", "admin"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    with engine.connect() as conn:
        affected_rows = conn.execute(
            select(enrollments).where(
                enrollments.c.course_id == course_id, enrollments.c.status == "active"
            )
        ).fetchall()
        affected = [row.id for row in affected_rows]

        changed_at = datetime.now(timezone.utc)

        if affected:
            conn.execute(
                update(enrollments)
                .where(enrollments.c.id.in_(affected))
                .values(status="cancelled")
            )
            conn.execute(
                insert(enrollment_status_history),
                [{"enrollment_id": eid, "status": "cancelled", "changed_at": changed_at} for eid in affected],
            )
        conn.commit()

    for row in affected_rows:
        events.publish(
            "enrollment.cancelled",
            {
                "id": row.id,
                "user_id": row.user_id,
                "course_id": row.course_id,
                "status": "cancelled",
                "enrolled_at": row.enrolled_at,
            },
        )
        events.publish(
            "enrollment.status_changed",
            {"enrollment_id": row.id, "status": "cancelled", "changed_at": changed_at},
        )