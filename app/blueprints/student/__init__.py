from flask import Blueprint
bp = Blueprint("student", __name__, template_folder="templates")
from . import routes
@bp.get("/health")
def health():
    return "ok-student"