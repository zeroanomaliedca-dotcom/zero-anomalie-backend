from datetime import datetime, timezone

from app.extensions import db
from app.models.sector import Sector
from app.models.category import Category


class Anomaly(db.Model):
    __tablename__ = "anomalies"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    declaration_method = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(40), default="EN_ATTENTE", nullable=False, index=True)

    sector_id = db.Column(db.Integer, db.ForeignKey("sectors.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    latitude = db.Column(db.Numeric(10, 7), nullable=True)
    longitude = db.Column(db.Numeric(10, 7), nullable=True)
    location_address = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    treated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    photos = db.relationship("AnomalyPhoto", backref="anomaly", lazy=True, cascade="all, delete-orphan")
    histories = db.relationship("History", backref="anomaly", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        sector = db.session.get(Sector, self.sector_id)
        category = db.session.get(Category, self.category_id)

        return {
            "id": self.id,
            "reference": self.reference,
            "title": self.title,
            "description": self.description,
            "declaration_method": self.declaration_method,
            "status": self.status,
            "sector_id": self.sector_id,
            "sector_name": sector.name if sector else None,
            "category_id": self.category_id,
            "category_name": category.name if category else None,
            "technician_id": self.technician_id,
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "location_address": self.location_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "treated_at": self.treated_at.isoformat() if self.treated_at else None,
            "photos": [
                {"id": photo.id, "photo_type": photo.photo_type}
                for photo in self.photos
            ],
        }
