from flask_login import UserMixin
from ..extensions import db

class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"))
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"))

    student = db.relationship("Student", backref=db.backref("auth", uselist=False))
    teacher = db.relationship("Teacher", backref=db.backref("auth", uselist=False))