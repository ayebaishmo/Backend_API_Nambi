from extensions import db
from datetime import datetime, timedelta

class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    expires_at = db.Column(db.DateTime, nullable=True)
    last_activity = db.Column(db.DateTime, server_default=db.func.now())
    is_active = db.Column(db.Boolean, default=True)
    language = db.Column(db.String(10), default='en', nullable=False)  # User's preferred language
    
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')
    
    def is_expired(self):
        """Check if conversation has expired"""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False
    
    def extend_session(self, minutes=30):
        """Extend session expiration"""
        self.last_activity = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)
        self.updated_at = datetime.utcnow()
