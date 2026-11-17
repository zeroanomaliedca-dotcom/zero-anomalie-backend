
from datetime import datetime, timezone

from app.extensions import db


class AnomalyPhoto(db.Model):
    __tablename__ = "anomaly_photos"

    id = db.Column(db.Integer, primary_key=True)

    anomaly_id = db.Column(
        db.Integer,
        db.ForeignKey("anomalies.id"),
        nullable=False
    )

    file_path = db.Column(
        db.String(500),
        nullable=False
    )

    photo_type = db.Column(
        db.String(30),
        nullable=False
    )

    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    uploaded_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )
