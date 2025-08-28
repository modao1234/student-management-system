from flask import render_template, request, redirect, url_for, flash
from werkzeug.security import check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from ...extensions import db
from ...models.user import User
from . import bp
from functools import wraps
from flask import abort

def role_required(*roles):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return deco

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        u = User.query.filter_by(username=username).one_or_none()
        if u and check_password_hash(u.password_hash, password):
            login_user(u)
            if u.role == "student":
                return redirect(url_for("student.list_sections"))
            if u.role == "teacher":
                return redirect(url_for("teacher.my_sections"))
            return redirect(url_for("admin.courses"))
        flash("Incorrect username or password")
    return render_template("login.html")

@bp.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
