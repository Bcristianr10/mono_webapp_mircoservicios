import services
from flask import Blueprint, render_template, session, redirect, url_for, flash
from functools import wraps

users_bp = Blueprint("users", __name__)

ROLE_LABELS = {
    "student": "Estudiante",
    "instructor": "Docente",
    "admin": "Administrador",
}


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "token" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


@users_bp.route("/users")
@login_required
def list_users():
    if session.get("role") != "admin":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("index"))
    status, data = services.list_users(session["token"])
    if status != 200:
        flash("Error al cargar usuarios.", "danger")
        data = []
    return render_template("users/list.html", users=data, role_labels=ROLE_LABELS)
