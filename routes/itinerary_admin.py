from flask import Blueprint, request, jsonify
from extensions import db
from models.itinerary import Itinerary

itinerary_admin_bp = Blueprint("itinerary_admin", __name__, url_prefix="/api/admin/itineraries")


# ---------------- CREATE ----------------
@itinerary_admin_bp.route("/", methods=["POST"])
def create_itinerary():
    """
    Create itinerary
    ---
    tags:
      - Itineraries (Admin)
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - title
            - days
            - places
            - accommodation
            - transport
            - details
            - package_name
          properties:
            title:
              type: string
              example: "3 Days in Kampala"
            days:
              type: integer
              example: 3
            budget:
              type: number
              example: 500
            places:
              type: string
              example: "Kampala, Entebbe"
            accommodation:
              type: string
              example: "Hotel Africana"
            transport:
              type: string
              example: "Private car"
            details:
              type: string
              example: "Day 1: City tour..."
            package_name:
              type: string
              example: "Silver"
    responses:
      201:
        description: Itinerary created
        schema:
          type: object
          properties:
            message:
              type: string
              example: Itinerary created successfully
            id:
              type: integer
      400:
        description: Validation error
    """

    data = request.get_json() or {}

    required_fields = ["title", "days", "places", "accommodation", "transport", "details", "package_name"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

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

    return jsonify({"message": "Itinerary created successfully", "id": itinerary.id}), 201


# ---------------- GET ALL ----------------
@itinerary_admin_bp.route("/", methods=["GET"])
def get_itineraries():
    """
    Get all itineraries
    ---
    tags:
      - Itineraries (Admin)
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

    itinerary.title = data.get("title", itinerary.title)
    itinerary.days = data.get("days", itinerary.days)
    itinerary.budget = data.get("budget", itinerary.budget)
    itinerary.places = data.get("places", itinerary.places)
    itinerary.accommodation = data.get("accommodation", itinerary.accommodation)
    itinerary.transport = data.get("transport", itinerary.transport)
    itinerary.details = data.get("details", itinerary.details)
    itinerary.package_name = data.get("package_name", itinerary.package_name)

    db.session.commit()

    return jsonify({"message": "Itinerary updated successfully"}), 200


# ---------------- DELETE ----------------
@itinerary_admin_bp.route("/<int:id>", methods=["DELETE"])
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
