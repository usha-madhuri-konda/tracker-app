from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class LearningEntry(db.Model):
    __tablename__ = "learning_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    topic = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    hours_spent = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "topic": self.topic,
            "date": self.date.isoformat() if self.date else None,
            "hours_spent": self.hours_spent,
            "notes": self.notes,
        }


class JobSwitchStage(db.Model):
    __tablename__ = "job_switch_stages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    stage_name = db.Column(db.String(80), nullable=False)  # e.g. Applied, Interview, Offer
    status = db.Column(db.String(40), nullable=False, default="active")  # active, rejected, accepted
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "company": self.company,
            "stage_name": self.stage_name,
            "status": self.status,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
