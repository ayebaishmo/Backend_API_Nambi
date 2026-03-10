from flask import Blueprint, request, jsonify
from models.admin import Admin
from middleware.auth import generate_token

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/login", methods=["POST"])
def admin_login():
    """
    Admin Login
    ---
    tags:
      - Admin
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Ishmael"
            password:
              type: string
              example: "mypassword123"
    responses:
      200:
        description: Login successful
      401:
        description: Invalid credentials
    """
    data = request.get_json()

    if not data or not data.get("name") or not data.get("password"):
        return jsonify({"error": "Name and password are required"}), 400

    admin = Admin.query.filter_by(name=data["name"]).first()

    if not admin or not admin.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_token(admin.id)

    return jsonify({
        "message": "Login successful",
        "token": token,
        "admin": {
            "id": admin.id,
            "name": admin.name,
            "position": admin.position
        }
    })
