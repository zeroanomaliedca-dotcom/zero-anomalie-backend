
from app import create_app
from app.models import User, Sector
from app.services.permissions import (
    user_can_access_sector,
    get_accessible_sector_ids,
)

app = create_app()

with app.app_context():
    users = {
        username: User.query.filter_by(username=username).first()
        for username in [
            "admin",
            "chef_agadir",
            "chef_inzegane",
            "technicien1",
            "technicien2",
        ]
    }

    sectors = {
        sector.name: sector
        for sector in Sector.query.all()
    }

    for username, user in users.items():
        if not user:
            print(f"COMPTE INTROUVABLE : {username}")
            continue

        print(f"\n--- {username} ({user.role}) ---")
        print("Secteurs accessibles :", get_accessible_sector_ids(user))

        for sector_name, sector in sectors.items():
            allowed = user_can_access_sector(user, sector.id)
            print(f"{sector_name} : {'AUTORISE' if allowed else 'REFUSE'}")
