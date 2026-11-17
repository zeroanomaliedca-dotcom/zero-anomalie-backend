
from app import create_app
from app.extensions import db
from app.models import Sector, Category


SECTORS = [
    "AGADIR",
    "INZEGANE",
    "AIT MELLOUL",
]


# Liste officielle des catégories d'anomalies
CATEGORIES = [
    "PC / PCO",
    "SR / SRO",
    "Splitter / BR",
    "Chambre",
    "Poteaux",
    "Cable Arrachée",
    "GC",
    "MSAN",
    "Autre",
]


def seed_sectors():
    for name in SECTORS:
        existing = Sector.query.filter_by(name=name).first()

        if not existing:
            db.session.add(
                Sector(name=name, is_active=True)
            )
            print(f"Secteur ajouté : {name}")
        else:
            if not existing.is_active:
                existing.is_active = True
                print(f"Secteur réactivé : {name}")
            else:
                print(f"Secteur déjà existant : {name}")


def seed_categories():
    # Désactiver les anciennes catégories non retenues.
    # Ne jamais les supprimer : elles peuvent être liées
    # à des anomalies déjà enregistrées.
    for category in Category.query.all():
        if category.name not in CATEGORIES:
            if category.is_active:
                category.is_active = False
                print(f"Ancienne catégorie désactivée : {category.name}")

    # Ajouter ou réactiver les catégories officielles.
    for name in CATEGORIES:
        existing = Category.query.filter_by(name=name).first()

        if not existing:
            db.session.add(
                Category(name=name, is_active=True)
            )
            print(f"Nouvelle catégorie ajoutée : {name}")
        else:
            if not existing.is_active:
                existing.is_active = True
                print(f"Catégorie réactivée : {name}")
            else:
                print(f"Catégorie déjà active : {name}")


def main():
    app = create_app()

    with app.app_context():
        try:
            seed_sectors()
            seed_categories()

            db.session.commit()

            print("\nInitialisation terminée avec succès.")

        except Exception as error:
            db.session.rollback()
            print("\nErreur pendant l'initialisation :")
            print(error)


if __name__ == "__main__":
    main()
