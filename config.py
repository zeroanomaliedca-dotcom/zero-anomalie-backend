import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    # 1. Priorité à DATABASE_URL (Render/Neon)
    # 2. Sinon, construction locale (votre code actuel)
    if os.getenv("DATABASE_URL"):
        # Neon fournit une URL qui commence par postgresql://
        # SQLAlchemy avec psycopg2 attend postgresql+psycopg2://
        SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL").replace(
            "postgresql://", "postgresql+psycopg2://", 1
        )
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+psycopg://"
            f"{os.getenv('DB_USER')}:"
            f"{os.getenv('DB_PASSWORD')}@"
            f"localhost:{os.getenv('DB_PORT')}/"
            f"{os.getenv('DB_NAME')}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuration des fichiers uploadés
    UPLOAD_FOLDER = str(
        BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads")
    )
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024

    # Configuration Gmail
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in (
        "true", "1", "yes"
    )
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")