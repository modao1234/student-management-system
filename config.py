from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = "dev-secret"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{(BASE_DIR / 'student.db').as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False