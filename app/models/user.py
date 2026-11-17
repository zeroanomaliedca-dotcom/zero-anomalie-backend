
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.models.sector import user_sectors


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        index=True
    )

    full_name = db.Column(
        db.String(150),
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(30),
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Suppression logique : conserve les anciennes anomalies
    deleted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        default=None
    )

    sectors = db.relationship(
        "Sector",
        secondary=user_sectors,
        back_populates="users",
        lazy="select"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "sector_ids": [sector.id for sector in self.sectors],
            "sectors": [sector.name for sector in self.sectors],
            "is_active": self.is_active,
            "deleted_at": (
                self.deleted_at.isoformat()
                if self.deleted_at else None
            )
        }
