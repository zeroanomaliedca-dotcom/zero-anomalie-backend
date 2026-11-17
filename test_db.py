
from sqlalchemy import text
from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("SELECT 1"))
        print("CONNEXION POSTGRESQL REUSSIE")
        print("ZERO ANOMALIE - BASE DE DONNEES OK")
    except Exception as e:
        print("ERREUR DE CONNEXION :")
        print(e)
