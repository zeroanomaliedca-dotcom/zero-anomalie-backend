
from datetime import datetime, timezone

from app.extensions import db


class History(db.Model):
    __tablename__ = "history"

    id = db.Column(db.Integer, primary_key=True)

    anomaly_id = db.Column(
        db.Integer,
        db.ForeignKey("anomalies.id"),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    old_status = db.Column(db.String(40), nullable=True)

    new_status = db.Column(db.String(40), nullable=False)

    comment = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
