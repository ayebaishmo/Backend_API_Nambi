from datetime import datetime, timedelta
from extensions import db
from models.conversation import Conversation

class SessionManager:
    """Manage conversation sessions and cleanup"""
    
    SESSION_TIMEOUT_MINUTES = 30
    CLEANUP_THRESHOLD_DAYS = 90
    
    @staticmethod
    def get_or_create_session(session_id):
        """Get existing session or create new one — safe against race conditions."""
        conversation = Conversation.query.filter_by(session_id=session_id).first()

        if conversation:
            if conversation.is_expired():
                conversation.is_active = False
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
            else:
                try:
                    conversation.extend_session(SessionManager.SESSION_TIMEOUT_MINUTES)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
            return conversation

        # Try to create — handle race condition gracefully
        try:
            return SessionManager._create_new_session(session_id)
        except Exception:
            db.session.rollback()
            # Another thread already created it — just fetch it
            conv = Conversation.query.filter_by(session_id=session_id).first()
            if conv:
                return conv
            raise
    
    @staticmethod
    def _create_new_session(session_id):
        """Create a new conversation session"""
        conversation = Conversation(
            session_id=session_id,
            expires_at=datetime.utcnow() + timedelta(minutes=SessionManager.SESSION_TIMEOUT_MINUTES),
            last_activity=datetime.utcnow(),
            is_active=True
        )
        db.session.add(conversation)
        db.session.commit()
        return conversation
    
    @staticmethod
    def cleanup_old_sessions():
        """Clean up expired and old sessions"""
        threshold_date = datetime.utcnow() - timedelta(days=SessionManager.CLEANUP_THRESHOLD_DAYS)
        
        # Mark expired sessions as inactive
        expired_sessions = Conversation.query.filter(
            Conversation.expires_at < datetime.utcnow(),
            Conversation.is_active == True
        ).all()
        
        for session in expired_sessions:
            session.is_active = False
        
        # Delete very old inactive sessions (optional - for data retention)
        old_sessions = Conversation.query.filter(
            Conversation.created_at < threshold_date,
            Conversation.is_active == False
        ).all()
        
        deleted_count = len(old_sessions)
        for session in old_sessions:
            db.session.delete(session)
        
        db.session.commit()
        
        return {
            'expired_marked': len(expired_sessions),
            'old_deleted': deleted_count
        }
    
    @staticmethod
    def get_active_sessions_count():
        """Get count of active sessions"""
        return Conversation.query.filter_by(is_active=True).count()
