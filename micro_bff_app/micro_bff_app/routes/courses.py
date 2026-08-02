import services
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from functools import wraps

courses_bp = Blueprint("courses", __name__)

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


def instructor_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") not in ("instructor", "admin"):
            flash("Acceso denegado.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


@courses_bp.route("/courses")
@login_required
def list_courses():
    status, data = services.list_courses(session["token"])
    if status != 200:
        flash("Error al cargar cursos.", "danger")
        data = []
    enrolled_counts = {c["id"]: services.count_enrolled_for(session["token"], c["id"]) for c in data}
    return render_template("courses/list.html", courses=data, enrolled_counts=enrolled_counts)


@courses_bp.route("/courses/mine")
@login_required
@instructor_required
def my_courses():
    status, data = services.my_courses(session["token"])
    if status != 200:
        flash("Error al cargar tus cursos.", "danger")
        data = []
    enrolled_counts = {c["id"]: services.count_enrolled_for(session["token"], c["id"]) for c in data}
    return render_template("courses/mine.html", courses=data, enrolled_counts=enrolled_counts)


@courses_bp.route("/courses/<int:course_id>")
@login_required
def detail(course_id):
    token = session["token"]
    status, course = services.get_course(token, course_id)
    if status != 200:
        flash("Curso no encontrado.", "danger")
        return redirect(url_for("courses.list_courses"))

    enrolled_count = services.count_enrolled_for(token, course_id)

    students = None
    if session.get("role") == "admin" or (
        session.get("role") == "instructor" and course.get("instructor_id") == session.get("user_id")
    ):
        raw = services.enrollments_for_course(token, course_id)
        students = []
        for e in raw:
            _, user = services.get_user(token, e["user_id"])
            if user and "full_name" in user:
                students.append(user)

    return render_template(
        "courses/detail.html",
        course=course,
        enrolled_count=enrolled_count,
        students=students,
    )


@courses_bp.route("/courses/new", methods=["GET", "POST"])
@login_required
@instructor_required
def new_course():
    if request.method == "POST":
        status, data = services.create_course(
            session["token"],
            request.form["title"],
            request.form.get("description", ""),
            request.form["capacity"],
        )
        if status == 201:
            flash("Curso creado.", "success")
            return redirect(url_for("courses.list_courses"))
        flash(data.get("detail", "Error al crear curso."), "danger")

    return render_template("courses/form.html", course=None)


@courses_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
@instructor_required
def edit_course(course_id):
    token = session["token"]

    if request.method == "POST":
        status, data = services.update_course(
            token,
            course_id,
            request.form["title"],
            request.form.get("description", ""),
            request.form["capacity"],
        )
        if status == 200:
            flash("Curso actualizado.", "success")
            return redirect(url_for("courses.detail", course_id=course_id))
        flash(data.get("detail", "Error al actualizar."), "danger")

    status, course = services.get_course(token, course_id)
    if status != 200:
        flash("Curso no encontrado.", "danger")
        return redirect(url_for("courses.my_courses"))

    return render_template("courses/form.html", course=course)


@courses_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
@instructor_required
def deactivate_course(course_id):
    status = services.deactivate_course(session["token"], course_id)
    if status == 204:
        flash("Curso desactivado.", "info")
    else:
        flash("Error al desactivar el curso.", "danger")
    return redirect(url_for("courses.list_courses"))
