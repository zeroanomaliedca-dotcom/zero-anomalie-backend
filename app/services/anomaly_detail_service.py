
from app.extensions import db
from app.models import (
    Anomaly,
    Sector,
    Category,
    User,
    AnomalyPhoto,
    History,
)


def get_anomaly_details(anomaly):
    """
    Retourne les informations détaillées d'une anomalie,
    ses photos et son historique.
    """

    sector = db.session.get(Sector, anomaly.sector_id)
    category = db.session.get(Category, anomaly.category_id)
    technician = db.session.get(User, anomaly.technician_id)

    photos = (
        AnomalyPhoto.query
        .filter_by(anomaly_id=anomaly.id)
        .order_by(AnomalyPhoto.uploaded_at.asc())
        .all()
    )

    histories = (
        History.query
        .filter_by(anomaly_id=anomaly.id)
        .order_by(History.created_at.asc())
        .all()
    )

    photo_list = []

    for photo in photos:
        uploader = db.session.get(User, photo.uploaded_by)

        photo_list.append({
            "id": photo.id,
            "file_path": photo.file_path,
            "photo_type": photo.photo_type,
            "uploaded_at": (
                photo.uploaded_at.isoformat()
                if photo.uploaded_at else None
            ),
            "uploaded_by": (
                uploader.to_dict()
                if uploader else None
            ),
        })

    history_list = []

    for event in histories:
        user = db.session.get(User, event.user_id)

        history_list.append({
            "id": event.id,
            "old_status": event.old_status,
            "new_status": event.new_status,
            "comment": event.comment,
            "created_at": (
                event.created_at.isoformat()
                if event.created_at else None
            ),
            "user": (
                user.to_dict()
                if user else None
            ),
        })

    return {
        "id": anomaly.id,
        "reference": anomaly.reference,
        "title": anomaly.title,
        "description": anomaly.description,
        "declaration_method": anomaly.declaration_method,
        "status": anomaly.status,

        "sector": (
            {
                "id": sector.id,
                "name": sector.name,
            }
            if sector else None
        ),

        "category": (
            {
                "id": category.id,
                "name": category.name,
                "description": category.description,
            }
            if category else None
        ),

        "technician": (
            technician.to_dict()
            if technician else None
        ),

        "location": {
            "latitude": (
                float(anomaly.latitude)
                if anomaly.latitude is not None else None
            ),
            "longitude": (
                float(anomaly.longitude)
                if anomaly.longitude is not None else None
            ),
            "address": anomaly.location_address,
        },

        "created_at": (
            anomaly.created_at.isoformat()
            if anomaly.created_at else None
        ),

        "updated_at": (
            anomaly.updated_at.isoformat()
            if anomaly.updated_at else None
        ),

        "treated_at": (
            anomaly.treated_at.isoformat()
            if anomaly.treated_at else None
        ),

        "photos": photo_list,
        "history": history_list,
    }
