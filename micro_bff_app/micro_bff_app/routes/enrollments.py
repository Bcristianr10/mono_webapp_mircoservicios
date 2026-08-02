import services
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from functools import wraps

enrollments_bp = Blueprint("enrollments", __name__)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "token" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


@enrollments_bp.route("/enrollments")
@login_required
def my_enrollments():
    token = session["token"]
    status, enrollments = services.my_enrollments(token)
    if status != 200:
        flash("Error al cargar matrículas.", "danger")
        enrollments = []

    enriched = []
    for e in enrollments:
        _, course = services.get_course(token, e["course_id"])
        enriched.append({**e, "course": course if isinstance(course, dict) and "id" in course else None})

    return render_template("enrollments/list.html", enrollments=enriched)


@enrollments_bp.route("/enrollments/<int:course_id>/enroll", methods=["POST"])
@login_required
def enroll(course_id):
    status, data = services.enroll(session["token"], course_id)
    if status == 201:
        flash("Te inscribiste correctamente.", "success")
    else:
        flash(data.get("detail", "Error al inscribirse."), "warning")
    return redirect(request.referrer or url_for("courses.list_courses"))


@enrollments_bp.route("/enrollments/<int:course_id>/cancel", methods=["POST"])
@login_required
def cancel(course_id):
    status = services.cancel_enrollment(session["token"], course_id)
    if status == 204:
        flash("Inscripción cancelada.", "info")
    else:
        flash("Error al cancelar la matrícula.", "danger")
    return redirect(request.referrer or url_for("enrollments.my_enrollments"))


@enrollments_bp.route("/enrollments/course/<int:course_id>/cancel-all", methods=["POST"])
@login_required
def cancel_all(course_id):
    if session.get("role") not in ("instructor", "admin"):
        flash("Acceso denegado.", "danger")
        return redirect(url_for("index"))
    status = services.cancel_all_for_course(session["token"], course_id)
    if status == 204:
        flash("Todas las matrículas del curso canceladas.", "success")
    else:
        flash("Error al cancelar matrículas.", "danger")
    return redirect(request.referrer or url_for("courses.my_courses"))
