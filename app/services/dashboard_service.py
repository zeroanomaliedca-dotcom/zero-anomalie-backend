
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.models import Anomaly, Sector, Category
from app.services.permissions import get_accessible_sector_ids


STATUSES = [
    "EN_ATTENTE",
    "EN_COURS_DE_TRAITEMENT",
    "TRAITEE",
]


def get_dashboard_statistics(user):
    """Calcule les statistiques selon le profil connecte."""

    if not user or not user.is_active:
        return None

    query = Anomaly.query

    if user.role in ("ADMIN", "CHEF_SERVICE"):
        # ADMIN et CHEF_SERVICE voient toutes les anomalies.
        pass

    elif user.role == "CHEF_SECTEUR":
        sector_ids = get_accessible_sector_ids(user)

        if not sector_ids:
            query = query.filter(Anomaly.id == -1)
        else:
            query = query.filter(Anomaly.sector_id.in_(sector_ids))

    elif user.role == "TECHNICIEN":
        query = query.filter(Anomaly.technician_id == user.id)

    else:
        return None

    total = query.count()

    status_counts = {status: 0 for status in STATUSES}

    status_results = (
        query.with_entities(
            Anomaly.status,
            func.count(Anomaly.id)
        )
        .group_by(Anomaly.status)
        .all()
    )

    for status, count in status_results:
        status_counts[status] = count

    sector_results = (
        query.join(Sector, Anomaly.sector_id == Sector.id)
        .with_entities(
            Sector.id,
            Sector.name,
            func.count(Anomaly.id)
        )
        .group_by(Sector.id, Sector.name)
        .order_by(func.count(Anomaly.id).desc())
        .all()
    )

    by_sector = [
        {
            "sector_id": sector_id,
            "sector_name": sector_name,
            "count": count,
        }
        for sector_id, sector_name, count in sector_results
    ]

    category_results = (
        query.join(Category, Anomaly.category_id == Category.id)
        .with_entities(
            Category.id,
            Category.name,
            func.count(Anomaly.id)
        )
        .group_by(Category.id, Category.name)
        .order_by(func.count(Anomaly.id).desc())
        .all()
    )

    by_category = [
        {
            "category_id": category_id,
            "category_name": category_name,
            "count": count,
        }
        for category_id, category_name, count in category_results
    ]

    treated = status_counts["TRAITEE"]

    treatment_rate = (
        round((treated / total) * 100, 2)
        if total > 0 else 0
    )

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=29)

    daily_results = (
        query.filter(
            Anomaly.created_at >= datetime.combine(
                start_date,
                datetime.min.time(),
                tzinfo=timezone.utc
            )
        )
        .with_entities(
            func.date(Anomaly.created_at),
            func.count(Anomaly.id)
        )
        .group_by(func.date(Anomaly.created_at))
        .order_by(func.date(Anomaly.created_at))
        .all()
    )

    daily_counts = {
        str(day): count
        for day, count in daily_results
    }

    evolution = []

    for index in range(30):
        day = start_date + timedelta(days=index)

        evolution.append({
            "date": day.isoformat(),
            "count": daily_counts.get(day.isoformat(), 0),
        })

    recent_anomalies = (
        query.order_by(Anomaly.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "role": user.role,
        "total": total,
        "by_status": status_counts,
        "treatment_rate": treatment_rate,
        "by_sector": by_sector,
        "by_category": by_category,
        "evolution_30_days": evolution,
        "recent_anomalies": [
            anomaly.to_dict()
            for anomaly in recent_anomalies
        ],
    }
