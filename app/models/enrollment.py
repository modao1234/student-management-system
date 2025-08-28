from ..extensions import db

class Enrollment(db.Model):
    __tablename__ = "enrollment"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("section.id"), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="enrolled")
    __table_args__ = (
        db.UniqueConstraint("student_id", "section_id", name="uq_student_section"),
    )

    student = db.relationship("Student", back_populates="enrollments")
    section = db.relationship("Section", back_populates="enrollments")
    grades = db.relationship("Grade", back_populates="enrollment",
                             cascade="all, delete-orphan")

class Assessment(db.Model):
    __tablename__ = "assessment"
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey("section.id"), nullable=False)
    title = db.Column(db.String(64), nullable=False)       # 平时/期末/作业X
    weight = db.Column(db.Float, nullable=False)           # 0~1
    full_score = db.Column(db.Float, nullable=False, default=100.0)
    due_at = db.Column(db.DateTime)
    __table_args__ = (
        db.UniqueConstraint("section_id", "title", name="uq_assessment_title"),
        db.CheckConstraint("weight >= 0 AND weight <= 1", name="ck_weight_0_1"),
    )

    section = db.relationship("Section", back_populates="assessments")
    grades = db.relationship("Grade", back_populates="assessment",
                             cascade="all, delete-orphan")

class Grade(db.Model):
    __tablename__ = "grade"
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey("enrollment.id"), nullable=False)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessment.id"), nullable=False)
    score = db.Column(db.Float, nullable=False, default=0.0)
    commented_at = db.Column(db.DateTime)
    remark = db.Column(db.String(255))
    __table_args__ = (
        db.UniqueConstraint("enrollment_id", "assessment_id", name="uq_enroll_assessment"),
    )

    enrollment = db.relationship("Enrollment", back_populates="grades")
    assessment = db.relationship("Assessment", back_populates="grades")