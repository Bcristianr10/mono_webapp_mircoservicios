from functools import wraps

import services
from flask import Blueprint, flash, redirect, render_template, session, url_for

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
