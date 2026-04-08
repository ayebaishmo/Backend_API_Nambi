from flask import Blueprint, request, jsonify
from extensions import db
from models.booking import Booking
from middleware.auth import require_auth

bookings_bp = Blueprint("bookings", __name__, url_prefix="/api/bookings")


@bookings_bp.route("/", methods=["POST"])
def create_booking():
    """
    Create booking request
    ---
    tags:
      - Bookings
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - email
            - phone
          properties:
            name:
              type: string
              example: "John Doe"
            email:
              type: string
              example: "john@example.com"
            phone:
              type: string
              example: "+256700000000"
            destination:
              type: string
              example: "Kampala"
            days:
              type: integer
              example: 3
            budget:
              type: number
              example: 500
            package:
              type: string
              example: "Silver"
            message:
              type: string
              example: "I want cultural experiences"
            session_id:
              type: string
              example: "abc123"
    responses:
      201:
        description: Booking created
      400:
        description: Validation error
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Invalid request body"}), 400
        
        # Validate required fields
        required = ["name", "email", "phone"]
        if not all(field in data for field in required):
            return jsonify({"error": "Name, email, and phone are required"}), 400
        
        booking = Booking(
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            destination=data.get("destination"),
            days=data.get("days"),
            budget=data.get("budget"),
            package=data.get("package"),
            message=data.get("message"),
            session_id=data.get("session_id"),
            status="pending"
        )
        
        db.session.add(booking)
        db.session.commit()
        
        # Send automatic email notifications
        from services.email_service import EmailService
        
        # Notify staff
        EmailService.send_booking_notification(booking)
        
        # Send confirmation to customer
        EmailService.send_booking_confirmation_to_customer(booking)
        
        return jsonify({
            "message": "Booking request submitted successfully",
            "id": booking.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create booking: {str(e)}"}), 500


@bookings_bp.route("/", methods=["GET"])
@require_auth
def get_bookings():
    """
    Get all bookings (Admin only)
    ---
    tags:
      - Bookings
    responses:
      200:
        description: List of bookings
    """
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    
    return jsonify([{
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
        "created_at": b.created_at
    } for b in bookings]), 200


@bookings_bp.route("/<int:id>", methods=["GET"])
@require_auth
def get_booking(id):
    """
    Get single booking (Admin only)
    ---
    tags:
      - Bookings
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Booking details
      404:
        description: Booking not found
    """
    booking = Booking.query.get_or_404(id)
    
    return jsonify({
        "id": booking.id,
        "name": booking.name,
        "email": booking.email,
        "phone": booking.phone,
        "destination": booking.destination,
        "days": booking.days,
        "budget": booking.budget,
        "package": booking.package,
        "message": booking.message,
        "session_id": booking.session_id,
        "status": booking.status,
        "created_at": booking.created_at
    }), 200


@bookings_bp.route("/<int:id>/status", methods=["PUT"])
@require_auth
def update_booking_status(id):
    """
    Update booking status (Admin only)
    ---
    tags:
      - Bookings
    parameters:
      - name: id
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
    responses:
      200:
        description: Status updated
      400:
        description: Invalid status
      404:
        description: Booking not found
    """
    booking = Booking.query.get_or_404(id)
    data = request.get_json()
    
    status = data.get("status")
    if status not in ["pending", "confirmed", "cancelled"]:
        return jsonify({"error": "Invalid status"}), 400
    
    booking.status = status
    db.session.commit()
    
    return jsonify({"message": "Booking status updated successfully"}), 200
