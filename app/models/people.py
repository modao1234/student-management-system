from ..extensions import db

class Student(db.Model):
    __tablename__ = "student"
    id = db.Column(db.Integer, primary_key=True)
    student_no = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    major = db.Column(db.String(64))
    grade_year = db.Column(db.Integer)      # 年级
    enroll_year = db.Column(db.Integer)     # 入学年

    enrollments = db.relationship(
        "Enrollment", back_populates="student", cascade="all, delete-orphan"
    )

class Teacher(db.Model):
    __tablename__ = "teacher"
    id = db.Column(db.Integer, primary_key=True)
    teacher_no = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    dept = db.Column(db.String(64))
    title = db.Column(db.String(32))

    sections = db.relationship("Section", back_populates="teacher")