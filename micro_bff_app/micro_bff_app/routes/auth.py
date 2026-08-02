import os
import jwt as pyjwt
import services
from flask import Blueprint, render_template, request, session, redirect, url_for, flash

auth_bp = Blueprint("auth", __name__)

ROLE_LABELS = {
    "student": "Estudiante",
    "instructor": "Docente",
    "admin": "Administrador",
}


def _store_session(token_str):
    payload = pyjwt.decode(token_str, os.getenv("SECRET_KEY", "dev-secret-key"), algorithms=["HS256"])
    session["token"] = token_str
    session["user_id"] = int(payload["sub"])
    session["role"] = payload["role"]
    session["role_label"] = ROLE_LABELS.get(payload["role"], payload["role"])


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "token" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        status, data = services.login(request.form["email"], request.form["password"])
        if status == 200:
            _store_session(data["access_token"])
            s2, user = services.get_user(session["token"], session["user_id"])
            session["full_name"] = user.get("full_name", "") if s2 == 200 else ""
            return redirect(url_for("index"))
        flash(data.get("detail", "Credenciales incorrectas."), "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "token" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        status, data = services.register(
            request.form["full_name"],
            request.form["email"],
            request.form["password"],
            request.form.get("role", "student"),
        )
        if status == 201:
            flash("Cuenta creada. Inicia sesión.", "success")
            return redirect(url_for("auth.login"))
        flash(data.get("detail", "Error al registrar."), "danger")

    return render_template("auth/register.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))
