
from app.extensions import db


user_sectors = db.Table(
    "user_sectors",
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    ),
    db.Column(
        "sector_id",
        db.Integer,
        db.ForeignKey("sectors.id", ondelete="CASCADE"),
        primary_key=True
    )
)


class Sector(db.Model):
    __tablename__ = "sectors"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    users = db.relationship(
        "User",
        secondary=user_sectors,
        back_populates="sectors",
        lazy="select"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active
        }
