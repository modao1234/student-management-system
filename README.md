# Student Information Management

A minimal system for **course offering, enrollment, scheduling, assessments, and grading** with role-based pages (**Admin / Teacher / Student**).

---

## Tech Stack
- **Backend**: Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login
- **Templates/UI**: Jinja2 + Bootstrap 5
- **DB**: SQLite (default `student.db`)
- **Auth**: Session login, simple role check

---

## Implemented Features

### Common
- Login / logout; role-based navigation.
- **Account** page for Student/Teacher: view profile + **change password**.

### Student
- Course catalog by term; **enroll / drop** with capacity check & **time-conflict detection** (same term + weekday + overlapping time).
- **Timetable** weekly view (Mon–Sun).
- **My grades**: assessments & weighted total.

### Teacher
- My sections.
- **Assessments** (title/weight/full score) with validation (each weight ∈ (0,1], total ≤ 1).
- **Gradebook**: batch scoring per student × assessment.

### Admin
- **Courses** CRUD.
- **Sections** (course offering): assign course/teacher/term/capacity.
- **Scheduling (Timeslots)**: weekday (1–7), start/end time, room.
- **Students / Teachers** management (CRUD, search, sort, paginate).
- When creating Student/Teacher, the system **auto-provisions a User**:
  - **Username** = student_no / teacher_no
  - **Default password** = `123456`
  - **Role** bound to the profile

> Note: This is a demo. CSRF and advanced security are not enabled by default.

---

## Setup

```bash
# 1) Virtualenv & dependencies
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) Database (first-time)
flask db init        # only once in a fresh repo
flask db migrate -m "init schema"
flask db upgrade
```

### Run
```bash
flask run  # http://127.0.0.1:5000
```

### Create an admin account (one-time seed)
```bash
flask shell
```
```python
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models import User
db.session.add(User(username="admin", password_hash=generate_password_hash("123456"), role="admin"))
db.session.commit(); print("OK")
```

---

## Usage Examples

### A) Admin bootstraps data
1. Login as **admin / 123456** → Admin menus appear.
2. **Courses**: `/admin/courses` → add e.g., `CS101 / Intro to CS / 3`.
3. **Teachers**: `/admin/teachers` → add Teacher No. & Name  
   → login user auto-created: **username = teacher_no, password = 123456**.
4. **Students**: `/admin/students` → add Student No. & Name  
   → login user auto-created: **username = student_no, password = 123456**.
5. **Sections & scheduling**:  
   - `/admin/sections` → create Section (course, teacher, term e.g., `2025S`, capacity).  
   - Click **Manage time** → add timeslots (weekday 1–7, HH:MM–HH:MM, room).

### B) Student flow
1. Login with **student_no / 123456**.
2. `/student/sections?term=2025S` → **Enroll**; conflict detection enforced.
3. `/student/me/timetable` → weekly timetable.
4. `/student/me/grades` → assessments + weighted total.
5. `/student/account` → **change password**.

### C) Teacher flow
1. Login with **teacher_no / 123456**.
2. `/teacher/sections` → open a section.
3. **Assessments**: add items with weights (sum ≤ 1) & full scores.
4. **Gradebook**: input scores; students can see them.
5. `/teacher/account` → **change password**.

---

## Key URLs (after login)
- **Admin**: `/admin/courses`, `/admin/sections`, `/admin/students`, `/admin/teachers`
- **Teacher**: `/teacher/sections`, `/teacher/sections/<id>/assessments`, `/teacher/sections/<id>/gradebook`, `/teacher/account`
- **Student**: `/student/sections?term=YYYYS`, `/student/me/timetable`, `/student/me/grades`, `/student/account`
- **Auth**: `/auth/login`, `/auth/logout`
