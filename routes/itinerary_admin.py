from flask import Blueprint, request, jsonify
from extensions import db
from models.itinerary import Itinerary
from services.itinerary_validator import ItineraryValidator
from middleware.auth import require_auth

itinerary_admin_bp = Blueprint("itinerary_admin", __name__, url_prefix="/api/admin/itineraries")


# ---------------- CREATE ----------------
@itinerary_admin_bp.route("/", methods=["POST"])
def create_itinerary():
    """
    Create new itinerary (Admin only)
    ---
    tags:
      - Itineraries (Admin)
    operationId: createItinerary
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        description: Itinerary data
        schema:
          type: object
          required:
            - title
            - days
            - budget
            - places
            - accommodation
            - transport
            - details
            - package_name
          properties:
            title:
              type: string
              example: "5 Days Uganda Safari"
            days:
              type: integer
              example: 5
            budget:
              type: string
              example: "2000"
            places:
              type: string
              example: "Kampala, Murchison Falls"
            accommodation:
              type: string
              example: "Mid-range lodges"
            transport:
              type: string
              example: "4x4 Safari Vehicle"
            details:
              type: string
              example: "Day 1: Kampala city tour..."
            package_name:
              type: string
              example: "Silver"
    responses:
      201:
        description: Itinerary created successfully
        schema:
          type: object
          properties:
            message:
              type: string
            id:
              type: integer
            warnings:
              type: array
              items:
                type: string
      400:
        description: Validation failed
        schema:
          type: object
          properties:
            error:
              type: string
            errors:
              type: array
              items:
                type: string
            warnings:
              type: array
              items:
                type: string
      401:
        description: Unauthorized
    """
    # Manual auth check
    from middleware.auth import verify_token
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Authorization token required'}), 401
    if token.startswith('Bearer '):
        token = token[7:]
    admin_id = verify_token(token)
    if not admin_id:
        return jsonify({'error': 'Invalid or expired token'}), 401

    data = request.get_json() or {}

    required_fields = ["title", "days", "places", "accommodation", "transport", "details", "package_name"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    # Validate itinerary data
    validation_result = ItineraryValidator.validate_complete_itinerary(data)
    
    if not validation_result['valid']:
        return jsonify({
            "error": "Validation failed",
            "errors": validation_result['errors'],
            "warnings": validation_result['warnings']
        }), 400
    
    # Create itinerary
    itinerary = Itinerary(
        title=data["title"],
        days=data["days"],
        budget=data.get("budget"),
        places=data["places"],
        accommodation=data["accommodation"],
        transport=data["transport"],
        details=data["details"],
        package_name=data["package_name"]
    )

    db.session.add(itinerary)
    db.session.commit()

    response_data = {
        "message": "Itinerary created successfully",
        "id": itinerary.id
    }
    
    # Include warnings if any
    if validation_result['warnings']:
        response_data['warnings'] = validation_result['warnings']

    return jsonify(response_data), 201


# ---------------- GET ALL ----------------
@itinerary_admin_bp.route("/", methods=["GET"])
def get_itineraries():
    """
    Get all itineraries
    ---
    tags:
      - Itineraries (Admin)
    operationId: getAllItineraries
    responses:
      200:
        description: List of itineraries
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              title:
                type: string
              days:
                type: integer
              budget:
                type: number
              places:
                type: string
              accommodation:
                type: string
              transport:
                type: string
              details:
                type: string
              package_name:
                type: string
              created_at:
                type: string
    """

    itineraries = Itinerary.query.order_by(Itinerary.created_at.desc()).all()

    return jsonify([
        {
            "id": i.id,
            "title": i.title,
            "days": i.days,
            "budget": i.budget,
            "places": i.places,
            "accommodation": i.accommodation,
            "transport": i.transport,
            "details": i.details,
            "package_name": i.package_name,
            "created_at": i.created_at
        } for i in itineraries
    ]), 200


# ---------------- GET ONE ----------------
@itinerary_admin_bp.route("/<int:id>", methods=["GET"])
def get_itinerary(id):
    """
    Get single itinerary
    ---
    tags:
      - Itineraries (Admin)
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: Itinerary ID
        example: 1
    responses:
      200:
        description: Single itinerary found
        schema:
          type: object
          properties:
            id:
              type: integer
            title:
              type: string
            days:
              type: integer
            budget:
              type: number
            places:
              type: string
            accommodation:
              type: string
            transport:
              type: string
            details:
              type: string
            package_name:
              type: string
            created_at:
              type: string
      404:
        description: Itinerary not found
    """

    i = Itinerary.query.get_or_404(id)

    return jsonify({
        "id": i.id,
        "title": i.title,
        "days": i.days,
        "budget": i.budget,
        "places": i.places,
        "accommodation": i.accommodation,
        "transport": i.transport,
        "details": i.details,
        "package_name": i.package_name,
        "created_at": i.created_at
    }), 200



# ---------------- UPDATE ----------------
@itinerary_admin_bp.route("/<int:id>", methods=["PUT"])
@require_auth
def update_itinerary(id):
    """
    Update itinerary
    ---
    tags:
      - Itineraries (Admin)
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: Itinerary ID
        example: 1
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            title:
              type: string
            days:
              type: integer
            budget:
              type: number
            places:
              type: string
            accommodation:
              type: string
            transport:
              type: string
            details:
              type: string
            package_name:
              type: string
    responses:
      200:
        description: Itinerary updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Itinerary updated successfully
      404:
        description: Itinerary not found
    """

    itinerary = Itinerary.query.get_or_404(id)
    data = request.get_json() or {}

    # Prepare updated data for validation
    updated_data = {
        'days': data.get('days', itinerary.days),
        'budget': data.get('budget', itinerary.budget),
        'places': data.get('places', itinerary.places),
        'start_date': data.get('start_date')
    }
    
    # Validate updated data
    validation_result = ItineraryValidator.validate_complete_itinerary(updated_data)
    
    if not validation_result['valid']:
        return jsonify({
            "error": "Validation failed",
            "errors": validation_result['errors'],
            "warnings": validation_result['warnings']
        }), 400

    # Update itinerary
    itinerary.title = data.get("title", itinerary.title)
    itinerary.days = data.get("days", itinerary.days)
    itinerary.budget = data.get("budget", itinerary.budget)
    itinerary.places = data.get("places", itinerary.places)
    itinerary.accommodation = data.get("accommodation", itinerary.accommodation)
    itinerary.transport = data.get("transport", itinerary.transport)
    itinerary.details = data.get("details", itinerary.details)
    itinerary.package_name = data.get("package_name", itinerary.package_name)

    db.session.commit()

    response_data = {"message": "Itinerary updated successfully"}
    
    # Include warnings if any
    if validation_result['warnings']:
        response_data['warnings'] = validation_result['warnings']

    return jsonify(response_data), 200


# ---------------- DELETE ----------------
@itinerary_admin_bp.route("/<int:id>", methods=["DELETE"])
@require_auth
def delete_itinerary(id):
    """
    Delete itinerary
    ---
    tags:
      - Itineraries (Admin)
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: Itinerary ID
        example: 1
    responses:
      200:
        description: Itinerary deleted successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Itinerary deleted successfully
      404:
        description: Itinerary not found
    """

    itinerary = Itinerary.query.get_or_404(id)

    db.session.delete(itinerary)
    db.session.commit()

    return jsonify({"message": "Itinerary deleted successfully"}), 200
