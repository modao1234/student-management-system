from flask import Blueprint
bp = Blueprint("teacher", __name__, template_folder="templates")
from . import routes
@bp.get("/health")
def health():
    return "ok-teacher"