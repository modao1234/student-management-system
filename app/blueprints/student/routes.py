from flask import render_template, request, redirect, url_for, flash
from ...extensions import db
from flask_login import login_required, current_user
from app.blueprints.auth.routes import role_required
from ...models import Section, Course, Teacher, Timeslot, Enrollment, Assessment, Grade, Student
from . import bp
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

def get_current_student():
    return current_user.student

def timeslot_overlap(a, b):
    if a.weekday != b.weekday:
        return False
    return not (a.end_time <= b.start_time or b.end_time <= a.start_time)

@bp.get("/sections")
@login_required
@role_required("student")
def list_sections():
    term = (request.args.get("term") or "").strip()
    kw   = (request.args.get("q") or "").strip()
    sort = request.args.get("sort", "course")
    order= request.args.get("order", "asc")
    page = max(request.args.get("page", type=int) or 1, 1)
    per  = min(max(request.args.get("per_page", type=int) or 10, 1), 100)

    q = Section.query.join(Course).join(Teacher).options(
        selectinload(Section.course), selectinload(Section.teacher), selectinload(Section.timeslots)
    )
    if term: q = q.filter(Section.term == term)
    if kw:
        like = f"%{kw}%"
        q = q.filter(or_(Course.name.ilike(like), Course.code.ilike(like), Teacher.name.ilike(like)))

    sort_map = {"course": Course.name, "teacher": Teacher.name, "cap": Section.capacity}
    col = sort_map.get(sort, Course.name)
    q = q.order_by(col.desc() if order == "desc" else col.asc())

    total = q.count()
    sections = q.offset((page-1)*per).limit(per).all()
    pages = (total + per - 1)//per

    counts = {s.id: Enrollment.query.filter_by(section_id=s.id).count() for s in sections}
    stu = get_current_student()
    my_enroll = {e.section_id: e.id for e in Enrollment.query.filter_by(student_id=stu.id).all()}

    return render_template("sections_student.html", sections=sections, counts=counts, term=term,
                           my_enroll=my_enroll, q=kw, sort=sort, order=order,
                           page=page, per_page=per, total=total, pages=pages)

@bp.post("/sections/<int:section_id>/enroll")
@login_required
@role_required("student")
def enroll(section_id):
    stu = get_current_student()
    sec = db.session.get(Section, section_id)
    if not sec:
        flash("Class does not exist"); return redirect(url_for("student.list_sections"))

    cur = Enrollment.query.filter_by(section_id=section_id).count()
    if cur >= sec.capacity:
        flash("Full"); return redirect(url_for("student.list_sections", term=sec.term))

    my_enrolls = Enrollment.query.options(
        selectinload(Enrollment.section).selectinload(Section.timeslots),
        selectinload(Enrollment.section).selectinload(Section.course),
    ).join(Section).filter(
        Enrollment.student_id == stu.id,
        Section.term == sec.term
    ).all()

    for en in my_enrolls:
        for t1 in en.section.timeslots:
            for t2 in sec.timeslots:
                if timeslot_overlap(t1, t2):
                    msg = f"Conflict with selected courses {en.section.course.name} : {t1.weekday} {t1.start_time.strftime('%H:%M')}-{t1.end_time.strftime('%H:%M')}"
                    flash(msg)
                    return redirect(url_for("student.list_sections", term=sec.term))

    e = Enrollment(student_id=stu.id, section_id=section_id, status="enrolled")
    db.session.add(e)
    try:
        db.session.commit()
        flash("Enroll was successful")
    except IntegrityError:
        db.session.rollback()
        flash("Already enrolled")
    return redirect(url_for("student.list_sections", term=sec.term))

@bp.post("/enrollments/<int:enroll_id>/drop")
@login_required
@role_required("student")
def drop(enroll_id):
    stu = get_current_student()
    e = db.session.get(Enrollment, enroll_id)
    if not e or e.student_id != stu.id:
        flash("No permission or record does not exist")
        return redirect(url_for("student.list_sections"))
    term = e.section.term
    db.session.delete(e)
    db.session.commit()
    flash("Dropped")
    return redirect(url_for("student.list_sections", term=term))

@bp.get("/me/timetable")
@login_required
@role_required("student")
def my_timetable():
    stu = get_current_student()
    enrolls = Enrollment.query.options(
        selectinload(Enrollment.section).selectinload(Section.course),
        selectinload(Enrollment.section).selectinload(Section.timeslots)
    ).filter_by(student_id=stu.id).all()
    table = {i: [] for i in range(1, 8)}
    for en in enrolls:
        sec = en.section
        for ts in sec.timeslots:
            table[ts.weekday].append({
                "course": sec.course.name,
                "code": sec.course.code,
                "start": ts.start_time.strftime("%H:%M"),
                "end": ts.end_time.strftime("%H:%M"),
                "room": ts.room,
                "term": sec.term
            })
    for w in table:
        table[w].sort(key=lambda x: x["start"])
    return render_template("timetable.html", table=table)

@bp.get("/me/grades")
@login_required
@role_required("student")
def my_grades():
    stu = get_current_student()
    enrolls = Enrollment.query.options(
        selectinload(Enrollment.section).selectinload(Section.course),
        selectinload(Enrollment.section).selectinload(Section.assessments),
        selectinload(Enrollment.grades).selectinload(Grade.assessment)
    ).filter_by(student_id=stu.id).all()

    courses = []
    for en in enrolls:
        sec = en.section
        score_map = {g.assessment_id: g.score for g in en.grades}
        rows = []
        total = 0.0
        for a in sec.assessments:
            score = score_map.get(a.id)
            rows.append({
                "title": a.title, "weight": a.weight,
                "full": a.full_score, "score": score
            })
            if score is not None:
                total += (score / a.full_score) * a.weight
        courses.append({
            "course": f"{sec.course.name} ({sec.course.code})",
            "term": sec.term,
            "rows": rows,
            "total_percent": round(total * 100, 2)
        })
    return render_template("grades.html", courses=courses)

@bp.route("/account", methods=["GET", "POST"])
@login_required
@role_required("student")
def account():
    u = current_user
    s = u.student
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
            return redirect(url_for("student.account"))
    return render_template("account_student.html", user=u, person=s)