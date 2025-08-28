from flask import render_template, request, redirect, url_for, flash
from sqlalchemy.orm import selectinload
from ...extensions import db
from app.blueprints.auth.routes import role_required
from flask_login import login_required
from ...models import Course, Section, Student, Teacher, Timeslot
from ...models.user import User
from werkzeug.security import generate_password_hash
from . import bp
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from datetime import datetime

@bp.get("/courses")
@login_required
@role_required("admin")
def courses():
    items = Course.query.order_by(Course.code).all()
    return render_template("courses.html", items=items)

@bp.post("/courses")
@login_required
@role_required("admin")
def create_course():
    code = request.form.get("code","").strip()
    name = request.form.get("name","").strip()
    credits = int(request.form.get("credits","0") or 0)
    if not code or not name:
        flash("Course code and name are required"); return redirect(url_for("admin.courses"))
    db.session.add(Course(code=code, name=name, credits=credits or 0))
    db.session.commit(); flash("Course created")
    return redirect(url_for("admin.courses"))

@bp.post("/courses/<int:cid>/delete")
@login_required
@role_required("admin")
def delete_course(cid):
    c = db.session.get(Course, cid)
    if not c: flash("Course does not exist"); return redirect(url_for("admin.courses"))
    db.session.delete(c); db.session.commit(); flash("Deleted course")
    return redirect(url_for("admin.courses"))

@bp.get("/sections")
def sections():
    term = (request.args.get("term") or "").strip()
    kw   = (request.args.get("q") or "").strip()
    sort = request.args.get("sort", "term")
    order= request.args.get("order", "desc")
    page = max(request.args.get("page", type=int) or 1, 1)
    per  = min(max(request.args.get("per_page", type=int) or 10, 1), 100)

    q = Section.query.join(Course).join(Teacher)
    if term:
        q = q.filter(Section.term == term)
    if kw:
        like = f"%{kw}%"
        q = q.filter(or_(
            Course.name.ilike(like), Course.code.ilike(like), Teacher.name.ilike(like)
        ))

    sort_map = {
        "term": Section.term,
        "course": Course.name,
        "teacher": Teacher.name,
        "cap": Section.capacity,
    }
    col = sort_map.get(sort, Section.term)
    q = q.order_by(col.desc() if order == "desc" else col.asc())

    total = q.count()
    items = q.offset((page - 1) * per).limit(per).all()
    pages = (total + per - 1) // per

    courses = Course.query.order_by(Course.code).all()
    teachers = Teacher.query.order_by(Teacher.teacher_no).all()

    return render_template("sections_admin.html",
        sections=items, courses=courses, teachers=teachers,
        term=term, q=kw, sort=sort, order=order,
        page=page, per_page=per, total=total, pages=pages
    )

@bp.post("/sections")
@login_required
@role_required("admin")
def create_section():
    course_id = request.form.get("course_id", type=int)
    teacher_id = request.form.get("teacher_id", type=int)
    term = (request.form.get("term") or "").strip()
    capacity = request.form.get("capacity", type=int) or 60
    if not (course_id and teacher_id and term):
        flash("Course/Teacher/Semester Required"); return redirect(url_for("admin.sections"))
    if capacity <= 0:
        flash("Capacity must be a positive integer"); return redirect(url_for("admin.sections"))
    if not db.session.get(Course, course_id) or not db.session.get(Teacher, teacher_id):
        flash("The course or teacher does not exist"); return redirect(url_for("admin.sections"))
    db.session.add(Section(course_id=course_id, teacher_id=teacher_id, term=term, capacity=capacity))
    db.session.commit(); flash("Classes have been created")
    return redirect(url_for("admin.sections"))

@bp.post("/sections/<int:sid>/delete")
@login_required
@role_required("admin")
def delete_section(sid):
    s = db.session.get(Section, sid)
    if not s: flash("Class does not exist"); return redirect(url_for("admin.sections"))
    db.session.delete(s); db.session.commit(); flash("Deleted class")
    return redirect(url_for("admin.sections"))

@bp.get("/sections/<int:sid>/timeslots", endpoint="timeslots")
@login_required
@role_required("admin")
def timeslots_page(sid):
    sec = (Section.query
           .options(selectinload(Section.timeslots),
                    selectinload(Section.course),
                    selectinload(Section.teacher))
           .get_or_404(sid))
    return render_template("timeslots.html", sec=sec)

@bp.post("/sections/<int:sid>/timeslots", endpoint="create_timeslot")
@login_required
@role_required("admin")
def create_timeslot(sid):
    weekday = request.form.get("weekday", type=int)
    start   = request.form.get("start")
    end     = request.form.get("end")
    room    = (request.form.get("room") or "").strip()

    try:
        t_start = datetime.strptime(start, "%H:%M").time()
        t_end   = datetime.strptime(end, "%H:%M").time()
    except Exception:
        flash("Time format must be HH:MM")
        return redirect(url_for("admin.timeslots", sid=sid))

    if weekday not in range(1, 8):
        flash("Weekday must be in 1..7")
        return redirect(url_for("admin.timeslots", sid=sid))
    if not (t_start < t_end):
        flash("End time must be later than start time")
        return redirect(url_for("admin.timeslots", sid=sid))

    db.session.add(Timeslot(section_id=sid, weekday=weekday,
                            start_time=t_start, end_time=t_end, room=room))
    db.session.commit()
    flash("Class time added")
    return redirect(url_for("admin.timeslots", sid=sid))

@bp.post("/timeslots/<int:tid>/delete", endpoint="delete_timeslot")
@login_required
@role_required("admin")
def delete_timeslot(tid):
    ts = db.session.get(Timeslot, tid)
    if not ts:
        flash("Timeslot does not exist")
        return redirect(url_for("admin.sections"))
    sid = ts.section_id
    db.session.delete(ts)
    db.session.commit()
    flash("Timeslot deleted")
    return redirect(url_for("admin.timeslots", sid=sid))

# ---------- Students ----------
@bp.get("/students")
@login_required
@role_required("admin")
def students():
    q     = (request.args.get("q") or "").strip()
    sort  = request.args.get("sort", "student_no")     # student_no|name|major|year|enroll
    order = request.args.get("order", "asc")           # asc|desc
    page  = max(request.args.get("page", type=int) or 1, 1)
    per   = min(max(request.args.get("per_page", type=int) or 10, 1), 100)

    query = Student.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Student.student_no.ilike(like),
            Student.name.ilike(like),
            Student.major.ilike(like),
        ))

    sort_map = {
        "student_no": Student.student_no,
        "name":       Student.name,
        "major":      Student.major,
        "year":       Student.grade_year,
        "enroll":     Student.enroll_year,
    }
    col = sort_map.get(sort, Student.student_no)
    query = query.order_by(col.desc() if order == "desc" else col.asc())

    total = query.count()
    items = query.offset((page-1)*per).limit(per).all()
    pages = max(1, (total + per - 1)//per)

    return render_template("students.html",
        items=items, q=q, sort=sort, order=order,
        page=page, per_page=per, total=total, pages=pages
    )

@bp.post("/students")
@login_required
@role_required("admin")
def create_student():
    student_no = (request.form.get("student_no") or "").strip()
    name       = (request.form.get("name") or "").strip()
    major      = (request.form.get("major") or "").strip()
    grade_year = request.form.get("grade_year", type=int)
    enroll_year= request.form.get("enroll_year", type=int)
    if not student_no or not name:
        flash("Student No. and Name are required")
        return redirect(url_for("admin.students"))
    s = Student(student_no=student_no, name=name, major=major,
                grade_year=grade_year, enroll_year=enroll_year)
    u = User(username=student_no,
             password_hash=generate_password_hash("123456"),
             role="student", student=s)
    db.session.add_all([s, u])
    try:
        db.session.commit(); flash("Student created")
    except IntegrityError:
        db.session.rollback(); flash("Student No. must be unique")
    return redirect(url_for("admin.students"))

@bp.post("/students/<int:sid>/update")
@login_required
@role_required("admin")
def update_student(sid):
    s = db.session.get(Student, sid)
    if not s:
        flash("Student not found"); return redirect(url_for("admin.students"))
    s.student_no = (request.form.get("student_no") or s.student_no).strip()
    s.name       = (request.form.get("name") or s.name).strip()
    s.major      = (request.form.get("major") or s.major).strip()
    gy           = request.form.get("grade_year")
    ey           = request.form.get("enroll_year")
    s.grade_year = int(gy) if gy not in (None, "",) else s.grade_year
    s.enroll_year= int(ey) if ey not in (None, "",) else s.enroll_year
    try:
        db.session.commit(); flash("Student updated")
    except IntegrityError:
        db.session.rollback(); flash("Student No. must be unique")
    return redirect(url_for("admin.students"))

@bp.post("/students/<int:sid>/delete")
@login_required
@role_required("admin")
def delete_student(sid):
    s = db.session.get(Student, sid)
    if not s:
        flash("Student not found"); return redirect(url_for("admin.students"))
    db.session.delete(s); db.session.commit(); flash("Student deleted")
    return redirect(url_for("admin.students"))

# ---------- Teachers ----------
@bp.get("/teachers")
@login_required
@role_required("admin")
def teachers():
    q     = (request.args.get("q") or "").strip()      # teacher_no/name/department/title
    sort  = request.args.get("sort", "teacher_no")     # teacher_no|name|dept|title
    order = request.args.get("order", "asc")
    page  = max(request.args.get("page", type=int) or 1, 1)
    per   = min(max(request.args.get("per_page", type=int) or 10, 1), 100)

    query = Teacher.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Teacher.teacher_no.ilike(like),
            Teacher.name.ilike(like),
            Teacher.dept.ilike(like),
            Teacher.title.ilike(like),
        ))

    sort_map = {
        "teacher_no": Teacher.teacher_no,
        "name":       Teacher.name,
        "dept":       Teacher.dept,
        "title":      Teacher.title,
    }
    col = sort_map.get(sort, Teacher.teacher_no)
    query = query.order_by(col.desc() if order == "desc" else col.asc())

    total = query.count()
    items = query.offset((page-1)*per).limit(per).all()
    pages = max(1, (total + per - 1)//per)

    return render_template("teachers.html",
        items=items, q=q, sort=sort, order=order,
        page=page, per_page=per, total=total, pages=pages
    )

@bp.post("/teachers")
@login_required
@role_required("admin")
def create_teacher():
    teacher_no = (request.form.get("teacher_no") or "").strip()
    name       = (request.form.get("name") or "").strip()
    dept       = (request.form.get("dept") or "").strip()
    title      = (request.form.get("title") or "").strip()
    if not teacher_no or not name:
        flash("Teacher No. and Name are required")
        return redirect(url_for("admin.teachers"))
    t = Teacher(teacher_no=teacher_no, name=name, dept=dept, title=title)
    u = User(username=teacher_no,
             password_hash=generate_password_hash("123456"),
             role="teacher", teacher=t)
    db.session.add_all([t, u])
    try:
        db.session.commit(); flash("Teacher created")
    except IntegrityError:
        db.session.rollback(); flash("Teacher No. must be unique")
    return redirect(url_for("admin.teachers"))

@bp.post("/teachers/<int:tid>/update")
@login_required
@role_required("admin")
def update_teacher(tid):
    t = db.session.get(Teacher, tid)
    if not t:
        flash("Teacher not found"); return redirect(url_for("admin.teachers"))
    t.teacher_no = (request.form.get("teacher_no") or t.teacher_no).strip()
    t.name       = (request.form.get("name") or t.name).strip()
    t.dept       = (request.form.get("dept") or t.dept).strip()
    t.title      = (request.form.get("title") or t.title).strip()
    try:
        db.session.commit(); flash("Teacher updated")
    except IntegrityError:
        db.session.rollback(); flash("Teacher No. must be unique")
    return redirect(url_for("admin.teachers"))

@bp.post("/teachers/<int:tid>/delete")
@login_required
@role_required("admin")
def delete_teacher(tid):
    t = db.session.get(Teacher, tid)
    if not t:
        flash("Teacher not found"); return redirect(url_for("admin.teachers"))
    db.session.delete(t); db.session.commit(); flash("Teacher deleted")
    return redirect(url_for("admin.teachers"))
