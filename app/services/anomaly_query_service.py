
from app.models import Anomaly
from app.services.permissions import get_accessible_sector_ids


def get_anomalies_for_user(user):
    """
    Retourne les anomalies accessibles selon le rôle :
    - ADMIN : toutes les anomalies.
    - CHEF_SECTEUR : anomalies de ses secteurs.
    - TECHNICIEN : uniquement ses propres déclarations.
    """

    if not user or not user.is_active:
        return []

    query = Anomaly.query

    if user.role == "ADMIN":
        pass

    elif user.role == "CHEF_SECTEUR":
        sector_ids = get_accessible_sector_ids(user)

        if not sector_ids:
            return []

        query = query.filter(Anomaly.sector_id.in_(sector_ids))

    elif user.role == "TECHNICIEN":
        query = query.filter(
            Anomaly.technician_id == user.id
        )

    else:
        return []

    return query.order_by(
        Anomaly.created_at.desc()
    ).all()
