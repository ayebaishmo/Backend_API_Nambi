"""
Human Handover Model
Tracks when users request to speak with a human agent
"""

from extensions import db
from datetime import datetime


class Handover(db.Model):
    """Handover requests from AI to human agents"""
    
    __tablename__ = 'handovers'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=False, index=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=True)
    itinerary_id = db.Column(db.Integer, db.ForeignKey('itineraries.id'), nullable=True)
    
    # User information
    user_message = db.Column(db.Text, nullable=True)
    user_email = db.Column(db.String(255), nullable=True)
    user_phone = db.Column(db.String(50), nullable=True)
    
    # Context
    conversation_summary = db.Column(db.Text, nullable=True)
    extracted_preferences = db.Column(db.JSON, nullable=True)
    
    # Status tracking
    status = db.Column(
        db.String(50), 
        default='pending',
        nullable=False
    )  # pending, contacted, resolved, cancelled
    
    priority = db.Column(
        db.String(20),
        default='medium',
        nullable=False
    )  # low, medium, high, urgent
    
    # Assignment
    assigned_to = db.Column(db.String(255), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    contacted_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Notes
    agent_notes = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'conversation_id': self.conversation_id,
            'itinerary_id': self.itinerary_id,
            'user_message': self.user_message,
            'user_email': self.user_email,
            'user_phone': self.user_phone,
            'conversation_summary': self.conversation_summary,
            'extracted_preferences': self.extracted_preferences,
            'status': self.status,
            'priority': self.priority,
            'assigned_to': self.assigned_to,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'contacted_at': self.contacted_at.isoformat() if self.contacted_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'agent_notes': self.agent_notes
        }
