from flask import render_template, request, redirect, url_for, flash
from ...extensions import db
from flask_login import login_required, current_user
from app.blueprints.auth.routes import role_required
from ...models import Section, Enrollment, Assessment, Grade, Teacher
from . import bp
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

def get_current_teacher():
    return current_user.teacher

@bp.get("/sections")
@login_required
@role_required("teacher")
def my_sections():
    t = get_current_teacher()
    secs = Section.query.options(
        selectinload(Section.course)
    ).filter_by(teacher_id=t.id).order_by(Section.term.desc()).all()
    return render_template("sections_teacher.html", sections=secs)

@bp.route("/sections/<int:section_id>/assessments", methods=["GET","POST"])
@login_required
@role_required("teacher")
def manage_assessments(section_id):
    sec = db.session.get(Section, section_id)
    if not sec:
        flash("Class does not exist")
        return redirect(url_for("teacher.sections"))

    if request.method == "POST":
        title  = (request.form.get("title") or "").strip()
        weight = request.form.get("weight", type=float)
        full   = request.form.get("full_score", type=float)

        if not title:
            flash("Title is required")
            return redirect(url_for("teacher.manage_assessments", section_id=section_id))
        if weight is None or not (0 < weight <= 1):
            flash("The weight must be between (0,1]")
            return redirect(url_for("teacher.manage_assessments", section_id=section_id))
        if full is None or full <= 0:
            flash("The full score must be greater than 0")
            return redirect(url_for("teacher.manage_assessments", section_id=section_id))

        total = (db.session.query(func.coalesce(func.sum(Assessment.weight), 0.0))
                 .filter(Assessment.section_id == section_id).scalar())
        if total + weight > 1 + 1e-6:
            flash("The sum of the weights of the assessment items in this class cannot exceed 1")
            return redirect(url_for("teacher.manage_assessments", section_id=section_id))

        db.session.add(Assessment(section_id=section_id, title=title, weight=weight, full_score=full))
        try:
            db.session.commit()
            flash("Added")
        except IntegrityError:
            db.session.rollback()
            flash("Failed to save (possibly duplicate title)")
        return redirect(url_for("teacher.manage_assessments", section_id=section_id))

    assessments = (Assessment.query
                   .filter_by(section_id=section_id)
                   .order_by(Assessment.id.asc()).all())
    total = (db.session.query(func.coalesce(func.sum(Assessment.weight), 0.0))
             .filter(Assessment.section_id == section_id).scalar())
    return render_template("assessments.html",
                           section=sec, assessments=assessments, total=total)
    
@bp.post("/assessments/<int:aid>/delete")
@login_required
@role_required("teacher")
def delete_assessment(aid):
    a = db.session.get(Assessment, aid)
    if not a:
        flash("Does not exist"); return redirect(url_for("teacher.my_sections"))
    sid = a.section_id
    db.session.delete(a); db.session.commit()
    flash("Deleted")
    return redirect(url_for("teacher.manage_assessments", section_id=sid))

@bp.route("/sections/<int:section_id>/gradebook", methods=["GET","POST"])
@login_required
@role_required("teacher")
def gradebook(section_id):
    sec = Section.query.options(
        selectinload(Section.course),
        selectinload(Section.assessments),
        selectinload(Section.enrollments).selectinload(Enrollment.student),
    ).get_or_404(section_id)

    if request.method == "POST":
        for en in sec.enrollments:
            for a in sec.assessments:
                key = f"scores-{en.id}-{a.id}"
                val = request.form.get(key)
                if val is None or val == "":
                    continue
                try:
                    score = float(val)
                except ValueError:
                    continue
                g = Grade.query.filter_by(enrollment_id=en.id, assessment_id=a.id).one_or_none()
                if g is None:
                    g = Grade(enrollment_id=en.id, assessment_id=a.id, score=score)
                    db.session.add(g)
                else:
                    g.score = score
        db.session.commit()
        flash("Saved scores")
        return redirect(url_for("teacher.gradebook", section_id=section_id))

    grade_map = {}
    for en in sec.enrollments:
        for g in en.grades:
            grade_map[(en.id, g.assessment_id)] = g.score

    return render_template("gradebook.html", section=sec, grade_map=grade_map)

@bp.route("/account", methods=["GET", "POST"])
@login_required
@role_required("teacher")
def account():
    u = current_user
    t = u.teacher
    if request.method == "POST":
        old = request.form.get("old_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if not check_password_hash(u.password_hash, old):
            flash("Current password is incorrect")
        elif len(new) < 6:
            flash("New password must be at least 6 characters")
        elif new != confirm:
            flash("Passwords do not match")
        else:
            u.password_hash = generate_password_hash(new)
            db.session.commit()
            flash("Password updated")
            return redirect(url_for("teacher.account"))
    return render_template("account_teacher.html", user=u, person=t)