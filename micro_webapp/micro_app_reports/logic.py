from sqlalchemy import select, func, and_, or_

from database.database import engine, users, courses, enrollments, enrollment_status_history

from datetime import datetime


def get_kpis() -> dict:
    with engine.connect() as conn:
        users_by_role = dict(
            conn.execute(select(users.c.role, func.count(users.c.id)).group_by(users.c.role)).all()
        )
        courses_active = conn.execute(
            select(func.count(courses.c.id)).where(courses.c.is_active == True)  # noqa: E712
        ).scalar_one()
        courses_inactive = conn.execute(
            select(func.count(courses.c.id)).where(courses.c.is_active == False)  # noqa: E712
        ).scalar_one()
        enrollments_active = conn.execute(
            select(func.count(enrollments.c.id)).where(enrollments.c.status == "active")
        ).scalar_one()
        enrollments_cancelled = conn.execute(
            select(func.count(enrollments.c.id)).where(enrollments.c.status == "cancelled")
        ).scalar_one()
        capacity_active_courses = conn.execute(
            select(func.coalesce(func.sum(courses.c.capacity), 0)).where(
                courses.c.is_active == True  # noqa: E712
            )
        ).scalar_one()

    utilization = (enrollments_active / capacity_active_courses * 100) if capacity_active_courses else 0

    return {
        "users_by_role": users_by_role,
        "total_users": sum(users_by_role.values()),
        "courses_active": courses_active,
        "courses_inactive": courses_inactive,
        "enrollments_active": enrollments_active,
        "enrollments_cancelled": enrollments_cancelled,
        "capacity_active_courses": capacity_active_courses,
        "utilization": round(utilization, 1),
    }


def course_enrollment_stats() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(
                courses.c.id,
                courses.c.title,
                courses.c.capacity,
                courses.c.instructor_id,
                func.count(enrollments.c.id),
            )
            .select_from(courses)
            .outerjoin(
                enrollments,
                and_(enrollments.c.course_id == courses.c.id, enrollments.c.status == "active"),
            )
            .where(courses.c.is_active == True)  # noqa: E712
            .group_by(courses.c.id)
        ).all()

    stats = []
    for course_id, title, capacity, instructor_id, active_count in rows:
        stats.append(
            {
                "id": course_id,
                "title": title,
                "capacity": capacity,
                "instructor_id": instructor_id,
                "active_count": active_count,
                "fill_rate": round((active_count / capacity * 100) if capacity else 0, 1),
            }
        )
    return stats


def top_courses(stats: list[dict], limit: int = 5) -> list[dict]:
    return sorted(stats, key=lambda c: c["active_count"], reverse=True)[:limit]


def courses_at_risk(stats: list[dict], threshold: float = 0.8) -> list[dict]:
    at_risk = [c for c in stats if c["capacity"] and c["active_count"] / c["capacity"] >= threshold]
    return sorted(at_risk, key=lambda c: c["fill_rate"], reverse=True)


def instructor_workload(stats: list[dict]) -> list[dict]:
    instructor_ids = {c["instructor_id"] for c in stats}
    if not instructor_ids:
        return []

    with engine.connect() as conn:
        instructors = dict(
            conn.execute(
                select(users.c.id, users.c.full_name).where(users.c.id.in_(instructor_ids))
            ).all()
        )

    by_instructor: dict[int, list[dict]] = {}
    for c in stats:
        by_instructor.setdefault(c["instructor_id"], []).append(c)

    workload = []
    for instructor_id, courses_list in by_instructor.items():
        total_students = sum(c["active_count"] for c in courses_list)
        avg_fill_rate = sum(c["fill_rate"] for c in courses_list) / len(courses_list)
        workload.append(
            {
                "instructor_id": instructor_id,
                "instructor_name": instructors.get(instructor_id, "Desconocido"),
                "course_count": len(courses_list),
                "total_students": total_students,
                "avg_fill_rate": round(avg_fill_rate, 1),
            }
        )

    return sorted(workload, key=lambda w: w["total_students"], reverse=True)


def top_students(limit: int = 5) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(users.c.id, users.c.full_name, users.c.email, func.count(enrollments.c.id))
            .select_from(users)
            .join(enrollments, and_(enrollments.c.user_id == users.c.id, enrollments.c.status == "active"))
            .where(users.c.role == "student")
            .group_by(users.c.id)
            .order_by(func.count(enrollments.c.id).desc())
            .limit(limit)
        ).all()

    return [
        {"id": uid, "full_name": full_name, "email": email, "active_enrollments": count}
        for uid, full_name, email, count in rows
    ]


def students_without_enrollments() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(users.c.id, users.c.full_name, users.c.email)
            .where(users.c.role == "student")
            .where(~users.c.id.in_(select(enrollments.c.user_id).where(enrollments.c.status == "active")))
            .order_by(users.c.created_at.desc())
        ).all()

    return [{"id": uid, "full_name": full_name, "email": email} for uid, full_name, email in rows]


def monthly_enrollment_trend(months: int = 6) -> list[dict]:
    month_expr = func.to_char(enrollments.c.enrolled_at, "YYYY-MM")
    with engine.connect() as conn:
        rows = conn.execute(
            select(month_expr, func.count(enrollments.c.id))
            .where(enrollments.c.enrolled_at.isnot(None))
            .group_by(month_expr)
            .order_by(month_expr)
        ).all()

    recent = rows[-months:]
    max_count = max((count for _, count in recent), default=0)

    return [
        {
            "month": month,
            "count": count,
            "bar_width": round((count / max_count * 100) if max_count else 0),
        }
        for month, count in recent
    ]


def cancellation_rate_by_course(limit: int = 10) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(enrollments.c.course_id, enrollments.c.status, func.count(enrollments.c.id)).group_by(
                enrollments.c.course_id, enrollments.c.status
            )
        ).all()

    by_course: dict[int, dict] = {}
    for course_id, status, count in rows:
        entry = by_course.setdefault(course_id, {"active": 0, "cancelled": 0})
        entry[status] = entry.get(status, 0) + count

    course_ids = [cid for cid, counts in by_course.items() if counts.get("cancelled", 0) > 0]
    if not course_ids:
        return []

    with engine.connect() as conn:
        titles = dict(
            conn.execute(select(courses.c.id, courses.c.title).where(courses.c.id.in_(course_ids))).all()
        )

    report = []
    for course_id in course_ids:
        counts = by_course[course_id]
        total = counts.get("active", 0) + counts.get("cancelled", 0)
        report.append(
            {
                "course_id": course_id,
                "title": titles.get(course_id, "Curso eliminado"),
                "active": counts.get("active", 0),
                "cancelled": counts.get("cancelled", 0),
                "cancellation_rate": round((counts["cancelled"] / total * 100) if total else 0, 1),
            }
        )

    return sorted(report, key=lambda r: r["cancellation_rate"], reverse=True)[:limit]


def cancellations_per_month(months: int = 6) -> list[dict]:
    month_expr = func.to_char(enrollment_status_history.c.changed_at, "YYYY-MM")
    with engine.connect() as conn:
        rows = conn.execute(
            select(month_expr, func.count(enrollment_status_history.c.id))
            .where(enrollment_status_history.c.status == "cancelled")
            .group_by(month_expr)
            .order_by(month_expr)
        ).all()

    recent = rows[-months:]
    max_count = max((count for _, count in recent), default=0)

    return [
        {
            "month": month,
            "count": count,
            "bar_width": round((count / max_count * 100) if max_count else 0),
        }
        for month, count in recent
    ]


def avg_days_to_cancellation_by_course(limit: int = 10, min_cancellations: int = 2) -> list[dict]:
    """Cursos donde los estudiantes cancelan mas rapido: señal de posible problema de calidad.

    Empareja cada 'cancelled' con el 'active' inmediatamente anterior del mismo
    enrollment_id (no con el enrolled_at actual de `enrollments`, que se
    sobrescribe si el alumno se re-matricula varias veces en el mismo curso).
    """
    with engine.connect() as conn:
        history_rows = conn.execute(
            select(
                enrollment_status_history.c.enrollment_id,
                enrollment_status_history.c.status,
                enrollment_status_history.c.changed_at,
                enrollments.c.course_id,
            )
            .select_from(enrollment_status_history)
            .join(enrollments, enrollments.c.id == enrollment_status_history.c.enrollment_id)
            .order_by(enrollment_status_history.c.enrollment_id, enrollment_status_history.c.changed_at)
        ).all()

    last_active_at: dict[int, datetime] = {}
    deltas_by_course: dict[int, list[float]] = {}

    for enrollment_id, status, changed_at, course_id in history_rows:
        if status == "active":
            last_active_at[enrollment_id] = changed_at
        elif status == "cancelled":
            started_at = last_active_at.pop(enrollment_id, None)
            if started_at is not None:
                seconds = (changed_at - started_at).total_seconds()
                deltas_by_course.setdefault(course_id, []).append(seconds)

    course_ids = [cid for cid, deltas in deltas_by_course.items() if len(deltas) >= min_cancellations]
    if not course_ids:
        return []

    with engine.connect() as conn:
        titles = dict(
            conn.execute(select(courses.c.id, courses.c.title).where(courses.c.id.in_(course_ids))).all()
        )

    report = []
    for course_id in course_ids:
        deltas = deltas_by_course[course_id]
        avg_seconds = sum(deltas) / len(deltas)
        report.append(
            {
                "course_id": course_id,
                "title": titles.get(course_id, "Curso eliminado"),
                "avg_days_to_cancel": round(avg_seconds / 86400, 1),
                "cancellations": len(deltas),
            }
        )

    return sorted(report, key=lambda r: r["avg_days_to_cancel"])[:limit]


def course_enrollment_detail(
    course_id: int, q: str | None = None, page: int = 1, page_size: int = 20
) -> dict:
    """Detalle paginado y filtrable de los matriculados de un curso, para la vista
    de drill-down del dashboard (busqueda + paginacion + exportacion)."""
    page = max(page, 1)
    offset = (page - 1) * page_size

    filters = [enrollments.c.course_id == course_id]
    if q:
        like = f"%{q}%"
        filters.append(or_(users.c.full_name.ilike(like), users.c.email.ilike(like)))

    base = (
        select(
            enrollments.c.id,
            users.c.full_name,
            users.c.email,
            enrollments.c.status,
            enrollments.c.enrolled_at,
        )
        .select_from(enrollments)
        .join(users, users.c.id == enrollments.c.user_id)
        .where(and_(*filters))
    )

    with engine.connect() as conn:
        total = conn.execute(select(func.count()).select_from(base.subquery())).scalar_one()

        rows = conn.execute(
            base.order_by(enrollments.c.enrolled_at.desc()).limit(page_size).offset(offset)
        ).all()

        course_title = conn.execute(
            select(courses.c.title).where(courses.c.id == course_id)
        ).scalar_one_or_none()

    items = [
        {
            "enrollment_id": eid,
            "full_name": full_name,
            "email": email,
            "status": status,
            "enrolled_at": enrolled_at.isoformat() if enrolled_at else None,
        }
        for eid, full_name, email, status, enrolled_at in rows
    ]

    return {
        "course_id": course_id,
        "course_title": course_title or "Curso eliminado",
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "query": q or "",
    }


def student_enrollment_detail(
    user_id: int, q: str | None = None, page: int = 1, page_size: int = 20
) -> dict:
    """Detalle paginado y filtrable de las matriculas de un estudiante (por titulo
    de curso), espejo de course_enrollment_detail para la vista de drill-down."""
    page = max(page, 1)
    offset = (page - 1) * page_size

    filters = [enrollments.c.user_id == user_id]
    if q:
        filters.append(courses.c.title.ilike(f"%{q}%"))

    base = (
        select(
            enrollments.c.id,
            courses.c.title,
            enrollments.c.status,
            enrollments.c.enrolled_at,
        )
        .select_from(enrollments)
        .join(courses, courses.c.id == enrollments.c.course_id)
        .where(and_(*filters))
    )

    with engine.connect() as conn:
        total = conn.execute(select(func.count()).select_from(base.subquery())).scalar_one()

        rows = conn.execute(
            base.order_by(enrollments.c.enrolled_at.desc()).limit(page_size).offset(offset)
        ).all()

        student = conn.execute(
            select(users.c.full_name, users.c.email).where(users.c.id == user_id)
        ).first()

    items = [
        {
            "enrollment_id": eid,
            "course_title": title,
            "status": status,
            "enrolled_at": enrolled_at.isoformat() if enrolled_at else None,
        }
        for eid, title, status, enrolled_at in rows
    ]

    return {
        "user_id": user_id,
        "student_name": student.full_name if student else "Estudiante eliminado",
        "student_email": student.email if student else "",
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "query": q or "",
    }
