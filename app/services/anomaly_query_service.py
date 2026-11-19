
from app.models import Anomaly


def get_anomalies_for_user(user):
    """
    Retourne les anomalies accessibles selon le rôle :

    - ADMIN : toutes les anomalies.
    - CHEF_SECTEUR : toutes les anomalies des trois secteurs.
    - TECHNICIEN : uniquement ses propres déclarations.
    """

    if (
        not user
        or not user.is_active
        or user.deleted_at is not None
    ):
        return []

    query = Anomaly.query

    if user.role in ("ADMIN", "CHEF_SECTEUR"):
        # ADMIN et CHEF_SECTEUR voient toutes les anomalies.
        pass

    elif user.role == "TECHNICIEN":
        # Le technicien voit uniquement ses déclarations.
        query = query.filter(
            Anomaly.technician_id == user.id
        )

    else:
        return []

    return query.order_by(
        Anomaly.created_at.desc()
    ).all()
