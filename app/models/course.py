from ..extensions import db

class Course(db.Model):
    __tablename__ = "course"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    credits = db.Column(db.Integer, nullable=False, default=2)

    sections = db.relationship("Section", back_populates="course")

class Section(db.Model):
    __tablename__ = "section"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    term = db.Column(db.String(16), nullable=False)  # 例如 "2025S"
    capacity = db.Column(db.Integer, default=60)

    course = db.relationship("Course", back_populates="sections")
    teacher = db.relationship("Teacher", back_populates="sections")
    enrollments = db.relationship("Enrollment", back_populates="section",
                                  cascade="all, delete-orphan")
    timeslots = db.relationship("Timeslot", back_populates="section",
                                cascade="all, delete-orphan")
    assessments = db.relationship("Assessment", back_populates="section",
                                  cascade="all, delete-orphan")

class Timeslot(db.Model):
    __tablename__ = "timeslot"
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey("section.id"), nullable=False)
    weekday = db.Column(db.Integer, nullable=False)  # 1=周一 ... 7=周日
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room = db.Column(db.String(64))

    section = db.relationship("Section", back_populates="timeslots")