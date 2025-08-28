from ..extensions import db
from .people import Student, Teacher
from .course import Course, Section, Timeslot
from .enrollment import Enrollment, Assessment, Grade
from .user import User

__all__ = [
    "Student", "Teacher", "Course", "Section", "Timeslot",
    "Enrollment", "Assessment", "Grade", "User",
]