"""
Human Handover Service
Manages the transition from AI to human agents
"""

from models.handover import Handover
from models.conversation import Conversation
from models.message import Message
from models.itinerary import Itinerary
from services.email_service import EmailService
from extensions import db
from datetime import datetime
import json


class HandoverService:
    """Manage handover requests from AI to human agents"""
    
    @staticmethod
    def create_handover_request(session_id, user_message=None, user_email=None, 
                                user_phone=None, itinerary_id=None, priority='medium'):
        """
        Create a new handover request
        
        Args:
            session_id: User's session ID
            user_message: Optional message from user
            user_email: User's email
            user_phone: User's phone number
            itinerary_id: Associated itinerary ID
            priority: low, medium, high, urgent
        
        Returns:
            Handover object
        """
        try:
            # Get conversation
            conversation = Conversation.query.filter_by(session_id=session_id).first()
            
            # Generate conversation summary
            conversation_summary = HandoverService._generate_conversation_summary(
                conversation.id if conversation else None
            )
            
            # Extract preferences from conversation
            extracted_preferences = HandoverService._extract_preferences_from_conversation(
                conversation.id if conversation else None
            )
            
            # Auto-determine priority based on budget/urgency
            if extracted_preferences:
                priority = HandoverService._determine_priority(extracted_preferences)
            
            # Create handover record
            handover = Handover(
                session_id=session_id,
                conversation_id=conversation.id if conversation else None,
                itinerary_id=itinerary_id,
                user_message=user_message,
                user_email=user_email,
                user_phone=user_phone,
                conversation_summary=conversation_summary,
                extracted_preferences=extracted_preferences,
                status='pending',
                priority=priority
            )
            
            db.session.add(handover)
            db.session.commit()
            
            # Send email notification
            HandoverService._send_notification(handover)
            
            return handover
            
        except Exception as e:
            print(f"Error creating handover: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def _generate_conversation_summary(conversation_id):
        """Generate a summary of the conversation"""
        if not conversation_id:
            return "No conversation history available"
        
        messages = Message.query.filter_by(
            conversation_id=conversation_id
        ).order_by(Message.created_at).all()
        
        if not messages:
            return "No messages in conversation"
        
        summary = []
        for msg in messages[-10:]:  # Last 10 messages
            role = "User" if msg.role == 'user' else "AI"
            timestamp = msg.created_at.strftime("%H:%M")
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            summary.append(f"[{timestamp}] {role}: {content}")
        
        return "\n".join(summary)
    
    @staticmethod
    def _extract_preferences_from_conversation(conversation_id):
        """Extract travel preferences from conversation"""
        if not conversation_id:
            return {}
        
        messages = Message.query.filter_by(
            conversation_id=conversation_id
        ).order_by(Message.created_at).all()
        
        if not messages:
            return {}
        
        # Combine all user messages
        user_text = ' '.join([
            msg.content for msg in messages if msg.role == 'user'
        ]).lower()
        
        preferences = {}
        
        # Extract duration
        import re
        duration_match = re.search(r'(\d+)\s*days?', user_text)
        if duration_match:
            preferences['duration'] = f"{duration_match.group(1)} days"
        
        # Extract budget
        budget_match = re.search(r'\$?\s*(\d+(?:,\d{3})*)', user_text)
        if budget_match:
            preferences['budget'] = f"${budget_match.group(1)}"
        
        # Extract interests
        interests = []
        interest_keywords = {
            'wildlife': ['safari', 'wildlife', 'animals', 'gorilla'],
            'culture': ['culture', 'cultural', 'traditional'],
            'adventure': ['adventure', 'hiking', 'rafting'],
            'relaxation': ['relax', 'peaceful', 'calm']
        }
        
        for interest, keywords in interest_keywords.items():
            if any(kw in user_text for kw in keywords):
                interests.append(interest)
        
        if interests:
            preferences['interests'] = ', '.join(interests)
        
        # Extract accommodation
        if 'luxury' in user_text:
            preferences['accommodation'] = 'Luxury'
        elif 'budget' in user_text:
            preferences['accommodation'] = 'Budget'
        elif 'mid-range' in user_text or 'midrange' in user_text:
            preferences['accommodation'] = 'Mid-range'
        
        return preferences
    
    @staticmethod
    def _determine_priority(preferences):
        """Determine priority based on preferences"""
        budget_str = preferences.get('budget', '$0')
        
        try:
            # Extract numeric value
            import re
            budget_match = re.search(r'(\d+(?:,\d{3})*)', budget_str)
            if budget_match:
                budget = int(budget_match.group(1).replace(',', ''))
                
                if budget >= 5000:
                    return 'urgent'  # High-value customer
                elif budget >= 2000:
                    return 'high'
                elif budget >= 1000:
                    return 'medium'
                else:
                    return 'low'
        except:
            pass
        
        return 'medium'
    
    @staticmethod
    def _send_notification(handover):
        """Send email notification about handover"""
        try:
            # Send email with handover object directly
            EmailService.send_handover_notification(handover)
            
        except Exception as e:
            print(f"Failed to send notification: {str(e)}")
    
    @staticmethod
    def get_pending_handovers():
        """Get all pending handover requests"""
        return Handover.query.filter_by(status='pending').order_by(
            Handover.created_at.desc()
        ).all()
    
    @staticmethod
    def update_handover_status(handover_id, status, agent_notes=None, assigned_to=None):
        """Update handover status"""
        handover = Handover.query.get(handover_id)
        if not handover:
            return None
        
        handover.status = status
        
        if agent_notes:
            handover.agent_notes = agent_notes
        
        if assigned_to:
            handover.assigned_to = assigned_to
        
        if status == 'contacted' and not handover.contacted_at:
            handover.contacted_at = datetime.utcnow()
        
        if status == 'resolved' and not handover.resolved_at:
            handover.resolved_at = datetime.utcnow()
        
        db.session.commit()
        return handover
