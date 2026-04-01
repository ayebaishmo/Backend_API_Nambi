"""
Admin Dashboard Routes
Unified endpoints for the admin to manage bookings, handovers, and itineraries
"""

from flask import Blueprint, request, jsonify
from extensions import db
from models.booking import Booking
from models.handover import Handover
from models.itinerary import Itinerary
from models.conversation import Conversation
from models.message import Message
from middleware.auth import require_auth
from datetime import datetime

admin_dashboard_bp = Blueprint("admin_dashboard", __name__, url_prefix="/api/admin/dashboard")


# ── OVERVIEW ─────────────────────────────────────────────────────────────────

@admin_dashboard_bp.route("/overview", methods=["GET"])
@require_auth
def overview():
    """
    Dashboard overview — counts for all sections
    ---
    tags:
      - Admin Dashboard
    security:
      - Bearer: []
    responses:
      200:
        description: Dashboard summary counts
    """
    try:
        bookings_total     = Booking.query.count()
        bookings_pending   = Booking.query.filter_by(status='pending').count()
        bookings_confirmed = Booking.query.filter_by(status='confirmed').count()
        bookings_cancelled = Booking.query.filter_by(status='cancelled').count()

        handovers_total    = Handover.query.count()
        handovers_pending  = Handover.query.filter_by(status='pending').count()
        handovers_active   = Handover.query.filter_by(status='contacted').count()
        handovers_resolved = Handover.query.filter_by(status='resolved').count()

        itineraries_total  = Itinerary.query.count()

        return jsonify({
            "bookings": {
                "total": bookings_total,
                "pending": bookings_pending,
                "confirmed": bookings_confirmed,
                "cancelled": bookings_cancelled
            },
            "handovers": {
                "total": handovers_total,
                "pending": handovers_pending,
                "active": handovers_active,
                "resolved": handovers_resolved
            },
            "itineraries": {
                "total": itineraries_total
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── BOOKINGS ──────────────────────────────────────────────────────────────────

@admin_dashboard_bp.route("/bookings", methods=["GET"])
@require_auth
def get_bookings():
    """
    Get all booking requests with optional status filter
    ---
    tags:
      - Admin Dashboard
    security:
      - Bearer: []
    parameters:
      - name: status
        in: query
        type: string
        enum: [pending, confirmed, cancelled]
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: List of bookings
    """
    try:
        status   = request.args.get('status')
        page     = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        query = Booking.query
        if status:
            query = query.filter_by(status=status)

        query = query.order_by(Booking.created_at.desc())
        total = query.count()
        bookings = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "bookings": [_booking_dict(b) for b in bookings],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_dashboard_bp.route("/bookings/<int:booking_id>", methods=["GET"])
@require_auth
def get_booking(booking_id):
    """
    Get single booking detail
    ---
    tags:
      - Admin Dashboard
    security:
      - Bearer: []
    parameters:
      - name: booking_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Booking detail
      404:
        description: Not found
    """
    booking = Booking.query.get_or_404(booking_id)
    return jsonify(_booking_dict(booking)), 200


@admin_dashboard_bp.route("/bookings/<int:booking_id>/status", methods=["PUT"])
@require_auth
def update_booking_status(booking_id):
    """
    Update booking status
    ---
    tags:
      - Admin Dashboard
    security:
      - Bearer: []
    parameters:
      - name: booking_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [pending, confirmed, cancelled]
            notes:
              type: string
    responses:
      200:
        description: Status updated
    """
    try:
        booking = Booking.query.get_or_404(booking_id)
        data = request.get_json() or {}
        status = data.get('status')

        if status not in ('pending', 'confirmed', 'cancelled'):
            return jsonify({"error": "Invalid status"}), 400

        booking.status = status
        db.session.commit()

        # Send email notification to customer on confirmation
        if status == 'confirmed':
            try:
                from services.email_service import EmailService
                EmailService.send_booking_confirmation_to_customer(booking)
            except Exception as e:
                print(f"Email notification failed: {e}")

        return jsonify({"message": f"Booking {status}", "booking": _booking_dict(booking)}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── HANDOVERS ─────────────────────────────────────────────────────────────────

@admin_dashboard_bp.route("/handovers", methods=["GET"])
@require_auth
def get_handovers():
    """
    Get all human handover requests
    ---
    tags:
      - Admin Dashboard
    security:
      - Bearer: []
    parameters:
      - name: status
        in: query
        type: string
        enum: [pending, contacted, resolved, cancelled]
      - name: priority
        in: query
        type: string
        enum: [low, medium, high, urgent]
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: List of handover requests
    """
    try:
        status   = request.args.get('status')
        priority = request.args.get('priority')
        page     = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        query = Handover.query
        if status:
            query = query.filter_by(status=status)
        if priority:
            query = query.filter_by(priority=priority)

        query = query.order_by(Handover.created_at.desc())
        total = query.count()
        handovers = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "handovers": [h.to_dict() for h in handovers],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_dashboard_bp.route("/handovers/<int:handover_id>", methods=["GET"])
@require_auth
def get_handover(handover_id):
    """
    Get handover detail including conversation history
    ---
    tags:
      - Admin Dashboard
    security:
      - Bearer: []
    parameters:
      - name: handover_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Handover detail with conversation
      404:
        description: Not found
    """
    try:
        handover = Handover.query.get_or_404(handover_id)
        result = handover.to_dict()

        # Attach conversation history so admin can see what was discussed
        if handover.session_id:
            conv = Conversation.query.filter_by(session_id=handover.session_id).first()
            if conv:
                messages = Message.query.filter_by(
                    conversation_id=conv.id
                ).order_by(Message.created_at).all()
                result['conversation'] = [
                    {
                        "role": m.role,
                        "content": m.content,
                        "created_at": m.created_at.isoformat() if m.created_at else None
                    }
                    for m in messages
                ]

        # Attach itinerary if linked
        if handover.itinerary_id:
            itin = Itinerary.query.get(handover.itinerary_id)
            if itin:
                result['itinerary'] = _itinerary_dict(itin)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_dashboard_bp.route("/handovers/<int:handover_id>/status", methods=["PUT"])
@require_auth
def update_handover_status(handover_id):
    """
    Update handover status and add agent notes
    ---
    tags:
      - Admin Dashboard
    security:
      - Bearer: []
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
        description: Handover updated
    """
    try:
        handover = Handover.query.get_or_404(handover_id)
        data = request.get_json() or {}

        if 'status' in data:
            new_status = data['status']
            if new_status not in ('pending', 'contacted', 'resolved', 'cancelled'):
                return jsonify({"error": "Invalid status"}), 400
            handover.status = new_status
            if new_status == 'contacted' and not handover.contacted_at:
                handover.contacted_at = datetime.utcnow()
            if new_status == 'resolved' and not handover.resolved_at:
                handover.resolved_at = datetime.utcnow()

        if 'agent_notes' in data:
            handover.agent_notes = data['agent_notes']
        if 'assigned_to' in data:
            handover.assigned_to = data['assigned_to']

        db.session.commit()
        return jsonify({"message": "Handover updated", "handover": handover.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── ITINERARIES ───────────────────────────────────────────────────────────────

@admin_dashboard_bp.route("/itineraries", methods=["GET"])
@require_auth
def get_itineraries():
    """
    Get all AI-generated itineraries
    ---
    tags:
      - Admin Dashboard
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: List of itineraries
    """
    try:
        page     = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        query = Itinerary.query.order_by(Itinerary.created_at.desc())
        total = query.count()
        itineraries = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "itineraries": [_itinerary_dict(i) for i in itineraries],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_dashboard_bp.route("/itineraries/<int:itinerary_id>", methods=["GET"])
@require_auth
def get_itinerary(itinerary_id):
    """
    Get single itinerary detail
    ---
    tags:
      - Admin Dashboard
    security:
      - Bearer: []
    parameters:
      - name: itinerary_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Itinerary detail
      404:
        description: Not found
    """
    itin = Itinerary.query.get_or_404(itinerary_id)
    return jsonify(_itinerary_dict(itin)), 200


@admin_dashboard_bp.route("/itineraries/<int:itinerary_id>", methods=["DELETE"])
@require_auth
def delete_itinerary(itinerary_id):
    """
    Delete an itinerary
    ---
    tags:
      - Admin Dashboard
    security:
      - Bearer: []
    parameters:
      - name: itinerary_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Deleted
      404:
        description: Not found
    """
    try:
        itin = Itinerary.query.get_or_404(itinerary_id)
        db.session.delete(itin)
        db.session.commit()
        return jsonify({"message": "Itinerary deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _booking_dict(b):
    return {
        "id": b.id,
        "name": b.name,
        "email": b.email,
        "phone": b.phone,
        "destination": b.destination,
        "days": b.days,
        "budget": b.budget,
        "package": b.package,
        "message": b.message,
        "session_id": b.session_id,
        "status": b.status,
        "created_at": b.created_at.isoformat() if b.created_at else None
    }


def _itinerary_dict(i):
    return {
        "id": i.id,
        "title": i.title,
        "days": i.days,
        "budget": i.budget,
        "places": i.places,
        "accommodation": i.accommodation,
        "transport": i.transport,
        "details": i.details,
        "package_name": i.package_name,
        "created_at": i.created_at.isoformat() if i.created_at else None
    }
