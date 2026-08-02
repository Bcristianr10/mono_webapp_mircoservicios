import csv
import io
from functools import wraps

import services
from flask import Blueprint, Response, flash, redirect, render_template, request, session, url_for

reports_bp = Blueprint("reports", __name__)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "token" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


@reports_bp.route("/reports")
@login_required
def dashboard():
    if session.get("role") != "admin":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("index"))

    status, data = services.get_reports_dashboard(session["token"])
    if status != 200:
        flash("Error al cargar los reportes.", "danger")
        return redirect(url_for("index"))

    return render_template("reports/dashboard.html", **data)


@reports_bp.route("/reports/courses/<int:course_id>")
@login_required
def course_detail(course_id):
    if session.get("role") != "admin":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("index"))

    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    status, data = services.get_course_enrollments(session["token"], course_id, q=q, page=page)
    if status != 200:
        flash("Error al cargar el detalle del curso.", "danger")
        return redirect(url_for("reports.dashboard"))

    return render_template("reports/course_detail.html", **data)


@reports_bp.route("/reports/courses/<int:course_id>/export.csv")
@login_required
def course_export_csv(course_id):
    if session.get("role") != "admin":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("index"))

    q = request.args.get("q", "").strip()
    status, data = services.get_course_enrollments(
        session["token"], course_id, q=q, page=1, page_size=1_000_000
    )
    if status != 200:
        flash("Error al generar el archivo.", "danger")
        return redirect(url_for("reports.course_detail", course_id=course_id))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Nombre", "Correo", "Estado", "Fecha de matricula"])
    for item in data["items"]:
        writer.writerow([item["full_name"], item["email"], item["status"], item["enrolled_at"]])

    filename = f"matriculas_curso_{course_id}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
