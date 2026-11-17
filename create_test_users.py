
from getpass import getpass

from app import create_app
from app.extensions import db
from app.models import User, Sector


TEST_USERS = [
    {
        "username": "admin",
        "full_name": "Administrateur ZERO ANOMALIE",
        "role": "ADMIN",
        "sectors": [],
    },
    {
        "username": "chef_agadir",
        "full_name": "Chef secteur AGADIR",
        "role": "CHEF_SECTEUR",
        "sectors": ["AGADIR"],
    },
    {
        "username": "chef_inzegane",
        "full_name": "Chef secteur INZEGANE et AIT MELLOUL",
        "role": "CHEF_SECTEUR",
        "sectors": ["INZEGANE", "AIT MELLOUL"],
    },
    {
        "username": "technicien1",
        "full_name": "Technicien de test 1",
        "role": "TECHNICIEN",
        "sectors": [],
    },
    {
        "username": "technicien2",
        "full_name": "Technicien de test 2",
        "role": "TECHNICIEN",
        "sectors": [],
    },
]


def ask_password(username):
    while True:
        password = getpass(f"Mot de passe pour {username} : ")
        confirmation = getpass("Confirmer le mot de passe : ")

        if len(password) < 8:
            print("Le mot de passe doit contenir au moins 8 caracteres.")
            continue

        if password != confirmation:
            print("Les deux mots de passe ne correspondent pas.")
            continue

        return password


def main():
    app = create_app()

    with app.app_context():
        try:
            sectors = {
                sector.name: sector
                for sector in Sector.query.all()
            }

            for user_data in TEST_USERS:
                for sector_name in user_data["sectors"]:
                    if sector_name not in sectors:
                        raise ValueError(
                            f"Secteur introuvable : {sector_name}"
                        )

            for user_data in TEST_USERS:
                username = user_data["username"]

                existing_user = User.query.filter_by(
                    username=username
                ).first()

                if existing_user:
                    print(f"Compte deja existant : {username}")
                    continue

                password = ask_password(username)

                user = User(
                    username=username,
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    is_active=True,
                )

                user.set_password(password)

                user.sectors = [
                    sectors[name]
                    for name in user_data["sectors"]
                ]

                db.session.add(user)

                print(f"Compte prepare : {username}")

            db.session.commit()

            print("\nCreation des comptes terminee.")

            for user in User.query.order_by(User.id).all():
                print(
                    f"{user.username} | {user.role} | "
                    f"{', '.join(s.name for s in user.sectors) or 'Aucun secteur fixe'}"
                )

        except Exception as error:
            db.session.rollback()
            print("\nERREUR :")
            print(error)


if __name__ == "__main__":
    main()
