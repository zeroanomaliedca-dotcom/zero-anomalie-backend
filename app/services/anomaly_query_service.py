
from app.models import Anomaly
from app.services.permissions import get_accessible_sector_ids


def get_anomalies_for_user(user, reference=None):
    """
    Retourne les anomalies accessibles selon le rôle :

    ADMIN et CHEF_SERVICE : toutes les anomalies.
    CHEF_SECTEUR : uniquement ses secteurs attribués.
    TECHNICIEN : uniquement ses propres déclarations.

    reference : filtre facultatif sur la référence.
    """

    if (
        not user
        or not user.is_active
        or user.deleted_at is not None
    ):
        return []

    query = Anomaly.query

    if user.role in ("ADMIN", "CHEF_SERVICE"):
        pass

    elif user.role == "CHEF_SECTEUR":
        sector_ids = get_accessible_sector_ids(user)

        if not sector_ids:
            return []

        query = query.filter(
            Anomaly.sector_id.in_(sector_ids)
        )

    elif user.role == "TECHNICIEN":
        query = query.filter(
            Anomaly.technician_id == user.id
        )

    else:
        return []

    if isinstance(reference, str) and reference.strip():
        query = query.filter(
            Anomaly.reference.ilike(
                f"%{reference.strip()}%"
            )
        )

    return query.order_by(
        Anomaly.created_at.desc()
    ).all()
