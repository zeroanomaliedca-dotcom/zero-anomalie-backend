
from app.models import Anomaly

from app.services.permissions import (
    ROLE_ADMIN,
    ROLE_CHEF,
    ROLE_CHEF_SERVICE,
    ROLE_TECHNICIEN,
)


def get_anomalies_for_user(user):
    """
    Retourne les anomalies accessibles selon le rôle :

    ADMIN et CHEF_SERVICE : toutes les anomalies.
    CHEF_SECTEUR : anomalies de ses secteurs accessibles.
    TECHNICIEN : uniquement ses propres déclarations.
    """

    if (
        not user
        or not user.is_active
        or user.deleted_at is not None
    ):
        return []

    query = Anomaly.query

    if user.role in (ROLE_ADMIN, ROLE_CHEF_SERVICE):
        pass

    elif user.role == ROLE_CHEF:
        from app.services.permissions import get_accessible_sector_ids

        sector_ids = get_accessible_sector_ids(user)

        if not sector_ids:
            return []

        query = query.filter(
            Anomaly.sector_id.in_(sector_ids)
        )

    elif user.role == ROLE_TECHNICIEN:
        query = query.filter(
            Anomaly.technician_id == user.id
        )

    else:
        return []

    return query.order_by(
        Anomaly.created_at.desc()
    ).all()
