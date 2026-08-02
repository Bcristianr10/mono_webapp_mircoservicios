import os
from flask import Flask, session, redirect, url_for
from routes.auth import auth_bp
from routes.courses import courses_bp
from routes.enrollments import enrollments_bp
from routes.users import users_bp
from routes.reports import reports_bp

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

app.register_blueprint(auth_bp)
app.register_blueprint(courses_bp)
app.register_blueprint(enrollments_bp)
app.register_blueprint(users_bp)
app.register_blueprint(reports_bp)


@app.route("/")
def index():
    if "token" not in session:
        return redirect(url_for("auth.login"))
    role = session.get("role")
    if role in ("instructor", "admin"):
        return redirect(url_for("courses.my_courses"))
    return redirect(url_for("enrollments.my_enrollments"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
