"""
Human Handover Routes
API endpoints for requesting human assistance
"""

from flask import Blueprint, request, jsonify
from services.handover_service import HandoverService
from models.handover import Handover
from middleware.rate_limit import rate_limit
from extensions import db
import os

handover_bp = Blueprint("handover", __name__)


@handover_bp.route("/request-human", methods=["POST"])
@rate_limit
def request_human_assistance():
    """
    Request human assistance (handover from AI to human agent)
    ---
    tags:
      - Human Handover
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - session_id
          properties:
            session_id:
              type: string
              example: "session_123"
            message:
              type: string
              example: "I need help customizing my itinerary"
            email:
              type: string
              example: "customer@example.com"
            phone:
              type: string
              example: "+256773539069"
            itinerary_id:
              type: integer
              example: 5
            priority:
              type: string
              enum: [low, medium, high, urgent]
              example: "medium"
    responses:
      200:
        description: Handover request created successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            handover_id:
              type: integer
            whatsapp_link:
              type: string
            email_sent:
              type: boolean
      400:
        description: Bad request
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request body"}), 400
        
        session_id = data.get("session_id")
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        
        user_message = data.get("message", "User requested human assistance")
        user_email = data.get("email")
        user_phone = data.get("phone")
        itinerary_id = data.get("itinerary_id")
        priority = data.get("priority", "medium")
        
        # Create handover request
        handover = HandoverService.create_handover_request(
            session_id=session_id,
            user_message=user_message,
            user_email=user_email,
            user_phone=user_phone,
            itinerary_id=itinerary_id,
            priority=priority
        )
        
        # Send automatic email notification to staff
        from services.email_service import EmailService
        EmailService.send_handover_notification(handover)
        
        # Generate WhatsApp link
        whatsapp_number = os.getenv('WHATSAPP_NUMBER', '')
        whatsapp_link = None
        if whatsapp_number:
            # Create pre-filled message
            message_text = f"Hi! I'm interested in booking a trip to Uganda. My reference ID is #{handover.id}"
            whatsapp_link = f"https://wa.me/{whatsapp_number.replace('+', '').replace(' ', '')}?text={message_text.replace(' ', '%20')}"
        
        return jsonify({
            "success": True,
            "message": "Your request has been sent to our travel experts! We'll contact you shortly.",
            "handover_id": handover.id,
            "whatsapp_link": whatsapp_link,
            "email_sent": True,
            "estimated_response_time": "Within 1 hour during business hours",
            "contact_methods": {
                "email": os.getenv('STAFF_EMAIL'),
                "whatsapp": whatsapp_number
            }
        }), 200
        
    except Exception as e:
        print(f"Error in request_human_assistance: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Failed to create handover request",
            "details": str(e)
        }), 500


@handover_bp.route("/handovers", methods=["GET"])
def get_handovers():
    """
    Get all handover requests (for admin)
    ---
    tags:
      - Human Handover
    parameters:
      - name: status
        in: query
        type: string
        enum: [pending, contacted, resolved, cancelled]
        description: Filter by status
      - name: priority
        in: query
        type: string
        enum: [low, medium, high, urgent]
        description: Filter by priority
    responses:
      200:
        description: List of handover requests
        schema:
          type: object
          properties:
            handovers:
              type: array
              items:
                type: object
            total:
              type: integer
    """
    try:
        status = request.args.get('status')
        priority = request.args.get('priority')
        
        query = Handover.query
        
        if status:
            query = query.filter_by(status=status)
        
        if priority:
            query = query.filter_by(priority=priority)
        
        handovers = query.order_by(Handover.created_at.desc()).all()
        
        return jsonify({
            "handovers": [h.to_dict() for h in handovers],
            "total": len(handovers)
        }), 200
        
    except Exception as e:
        print(f"Error in get_handovers: {str(e)}")
        return jsonify({"error": str(e)}), 500


@handover_bp.route("/handovers/<int:handover_id>", methods=["GET"])
def get_handover_details(handover_id):
    """
    Get details of a specific handover request
    ---
    tags:
      - Human Handover
    parameters:
      - name: handover_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Handover details
      404:
        description: Handover not found
    """
    try:
        handover = Handover.query.get_or_404(handover_id)
        
        # Include related data
        result = handover.to_dict()
        
        # Add itinerary if exists
        if handover.itinerary_id:
            from models.itinerary import Itinerary
            itinerary = Itinerary.query.get(handover.itinerary_id)
            if itinerary:
                result['itinerary'] = {
                    'id': itinerary.id,
                    'title': itinerary.title,
                    'days': itinerary.days,
                    'budget': itinerary.budget,
                    'places': itinerary.places
                }
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error in get_handover_details: {str(e)}")
        return jsonify({"error": str(e)}), 500


@handover_bp.route("/handovers/<int:handover_id>/update", methods=["PUT"])
def update_handover(handover_id):
    """
    Update handover status (for admin)
    ---
    tags:
      - Human Handover
    parameters:
      - name: handover_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [pending, contacted, resolved, cancelled]
            agent_notes:
              type: string
            assigned_to:
              type: string
    responses:
      200:
        description: Handover updated successfully
      404:
        description: Handover not found
    """
    try:
        data = request.get_json() or {}
        
        status = data.get('status')
        agent_notes = data.get('agent_notes')
        assigned_to = data.get('assigned_to')
        
        handover = HandoverService.update_handover_status(
            handover_id=handover_id,
            status=status,
            agent_notes=agent_notes,
            assigned_to=assigned_to
        )
        
        if not handover:
            return jsonify({"error": "Handover not found"}), 404
        
        return jsonify({
            "success": True,
            "message": "Handover updated successfully",
            "handover": handover.to_dict()
        }), 200
        
    except Exception as e:
        print(f"Error in update_handover: {str(e)}")
        return jsonify({"error": str(e)}), 500


@handover_bp.route("/handovers/stats", methods=["GET"])
def get_handover_stats():
    """
    Get handover statistics (for admin dashboard)
    ---
    tags:
      - Human Handover
    responses:
      200:
        description: Handover statistics
        schema:
          type: object
          properties:
            total:
              type: integer
            by_status:
              type: object
            by_priority:
              type: object
            avg_response_time:
              type: string
    """
    try:
        from sqlalchemy import func
        
        # Total handovers
        total = Handover.query.count()
        
        # By status
        by_status = {}
        status_counts = db.session.query(
            Handover.status, func.count(Handover.id)
        ).group_by(Handover.status).all()
        
        for status, count in status_counts:
            by_status[status] = count
        
        # By priority
        by_priority = {}
        priority_counts = db.session.query(
            Handover.priority, func.count(Handover.id)
        ).group_by(Handover.priority).all()
        
        for priority, count in priority_counts:
            by_priority[priority] = count
        
        # Average response time
        from datetime import timedelta
        contacted_handovers = Handover.query.filter(
            Handover.contacted_at.isnot(None)
        ).all()
        
        if contacted_handovers:
            total_time = sum([
                (h.contacted_at - h.created_at).total_seconds()
                for h in contacted_handovers
            ], 0)
            avg_seconds = total_time / len(contacted_handovers)
            avg_response_time = str(timedelta(seconds=int(avg_seconds)))
        else:
            avg_response_time = "N/A"
        
        return jsonify({
            "total": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "avg_response_time": avg_response_time,
            "pending_count": by_status.get('pending', 0)
        }), 200
        
    except Exception as e:
        print(f"Error in get_handover_stats: {str(e)}")
        return jsonify({"error": str(e)}), 500
