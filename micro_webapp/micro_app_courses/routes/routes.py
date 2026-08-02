import os
import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, insert, update
from typing import List
from database.database import engine, courses
from datetime import datetime, timezone
from schemas.schemas import CourseCreate, CourseOut, CourseUpdate

import events

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ENROLLMENTS_URL = os.getenv("ENROLLMENTS_URL", "http://micro_app_enrollments:8003")

courses_router = APIRouter()
bearer = HTTPBearer()


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        return jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido.")


def require_instructor_or_admin(token: dict):
    if token["role"] not in ("instructor", "admin"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")


@courses_router.get("/api/courses", response_model=List[CourseOut])
def list_courses(token: dict = Depends(decode_token)):
    with engine.connect() as conn:
        result = conn.execute(
            select(courses).where(courses.c.is_active == True).order_by(courses.c.created_at.desc())
        )
        return [CourseOut(**dict(zip(courses.c.keys(), row))) for row in result]


@courses_router.get("/api/courses/all", response_model=List[CourseOut])
def list_all_courses(token: dict = Depends(decode_token)):
    if token["role"] != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    with engine.connect() as conn:
        result = conn.execute(select(courses).order_by(courses.c.created_at.desc()))
        return [CourseOut(**dict(zip(courses.c.keys(), row))) for row in result]


@courses_router.get("/api/courses/mine", response_model=List[CourseOut])
def my_courses(token: dict = Depends(decode_token)):
    require_instructor_or_admin(token)
    instructor_id = int(token["sub"])

    with engine.connect() as conn:
        result = conn.execute(
            select(courses)
            .where(courses.c.instructor_id == instructor_id)
            .order_by(courses.c.created_at.desc())
        )
        return [CourseOut(**dict(zip(courses.c.keys(), row))) for row in result]


@courses_router.get("/api/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: int, token: dict = Depends(decode_token)):
    with engine.connect() as conn:
        course = conn.execute(select(courses).where(courses.c.id == course_id)).fetchone()

    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado.")

    return CourseOut(**dict(zip(courses.c.keys(), course)))


@courses_router.post("/api/courses", response_model=CourseOut, status_code=201)
def create_course(body: CourseCreate, token: dict = Depends(decode_token)):
    require_instructor_or_admin(token)

    with engine.connect() as conn:
        result = conn.execute(
            insert(courses).values(
                title=body.title,
                description=body.description,
                instructor_id=int(token["sub"]),
                capacity=body.capacity,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
        )
        conn.commit()
        course = conn.execute(select(courses).where(courses.c.id == result.inserted_primary_key[0])).fetchone()
        course_out = CourseOut(**dict(zip(courses.c.keys(), course)))

    events.publish("course.created", course_out.model_dump(mode="json"))
    return course_out


@courses_router.put("/api/courses/{course_id}", response_model=CourseOut)
def update_course(course_id: int, body: CourseUpdate, request: Request, token: dict = Depends(decode_token)):
    require_instructor_or_admin(token)

    with engine.connect() as conn:
        course = conn.execute(select(courses).where(courses.c.id == course_id)).fetchone()

        if course is None:
            raise HTTPException(status_code=404, detail="Curso no encontrado.")

        if token["role"] != "admin" and course.instructor_id != int(token["sub"]):
            raise HTTPException(status_code=403, detail="Solo el docente dueño puede editar este curso.")

        resp = httpx.get(
            f"{ENROLLMENTS_URL}/api/enrollments/course/{course_id}/count",
            headers={"Authorization": request.headers.get("authorization", "")},
            timeout=5,
        )
        enrolled_count = resp.json().get("count", 0) if resp.status_code == 200 else 0

        if body.capacity < enrolled_count:
            raise HTTPException(
                status_code=400,
                detail=f"El cupo no puede ser menor a {enrolled_count}, la cantidad de estudiantes ya matriculados.",
            )

        conn.execute(
            update(courses).where(courses.c.id == course_id).values(
                title=body.title,
                description=body.description,
                capacity=body.capacity,
            )
        )
        conn.commit()
        updated = conn.execute(select(courses).where(courses.c.id == course_id)).fetchone()
        course_out = CourseOut(**dict(zip(courses.c.keys(), updated)))

    events.publish("course.updated", course_out.model_dump(mode="json"))
    return course_out


@courses_router.delete("/api/courses/{course_id}", status_code=204)
def deactivate_course(course_id: int, request: Request, token: dict = Depends(decode_token)):
    require_instructor_or_admin(token)

    with engine.connect() as conn:
        course = conn.execute(select(courses).where(courses.c.id == course_id)).fetchone()

        if course is None:
            raise HTTPException(status_code=404, detail="Curso no encontrado.")

        if token["role"] != "admin" and course.instructor_id != int(token["sub"]):
            raise HTTPException(status_code=403, detail="Solo el docente dueño puede desactivar este curso.")

        conn.execute(update(courses).where(courses.c.id == course_id).values(is_active=False))
        conn.commit()
        deactivated = conn.execute(select(courses).where(courses.c.id == course_id)).fetchone()
        course_out = CourseOut(**dict(zip(courses.c.keys(), deactivated)))

    events.publish("course.deactivated", course_out.model_dump(mode="json"))

    httpx.delete(
        f"{ENROLLMENTS_URL}/api/enrollments/course/{course_id}/all",
        headers={"Authorization": request.headers.get("authorization", "")},
        timeout=5,
    )