from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert

from database.database import engine, users, courses, enrollments, enrollment_status_history


def _parse_dt(value):
    return datetime.fromisoformat(value) if value else None


def upsert_user(payload: dict) -> None:
    stmt = pg_insert(users).values(
        id=payload["id"],
        full_name=payload["full_name"],
        email=payload["email"],
        role=payload["role"],
        created_at=_parse_dt(payload.get("created_at")),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={"full_name": stmt.excluded.full_name, "email": stmt.excluded.email, "role": stmt.excluded.role},
    )
    with engine.begin() as conn:
        conn.execute(stmt)


def upsert_course(payload: dict) -> None:
    stmt = pg_insert(courses).values(
        id=payload["id"],
        title=payload["title"],
        description=payload.get("description"),
        instructor_id=payload["instructor_id"],
        capacity=payload["capacity"],
        is_active=payload["is_active"],
        created_at=_parse_dt(payload.get("created_at")),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "title": stmt.excluded.title,
            "description": stmt.excluded.description,
            "capacity": stmt.excluded.capacity,
            "is_active": stmt.excluded.is_active,
        },
    )
    with engine.begin() as conn:
        conn.execute(stmt)


def upsert_enrollment(payload: dict) -> None:
    stmt = pg_insert(enrollments).values(
        id=payload["id"],
        user_id=payload["user_id"],
        course_id=payload["course_id"],
        status=payload["status"],
        enrolled_at=_parse_dt(payload.get("enrolled_at")),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={"status": stmt.excluded.status, "enrolled_at": stmt.excluded.enrolled_at},
    )
    with engine.begin() as conn:
        conn.execute(stmt)


def append_status_history(payload: dict) -> None:
    stmt = pg_insert(enrollment_status_history).values(
        enrollment_id=payload["enrollment_id"],
        status=payload["status"],
        changed_at=_parse_dt(payload.get("changed_at")),
    )
    # Idempotente: si el mismo evento se reprocesa (redelivery), no duplica la fila.
    stmt = stmt.on_conflict_do_nothing(index_elements=["enrollment_id", "status", "changed_at"])
    with engine.begin() as conn:
        conn.execute(stmt)
