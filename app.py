import os
from flask import Flask, jsonify
from dotenv import load_dotenv
from extensions import cors, swagger, db, bcrypt
from routes.chat import chat_bp
from routes.admin_auth import admin_auth_bp
from routes.admin_login import admin_bp
from routes.itinerary_admin import itinerary_admin_bp
from routes.bookings import bookings_bp
from routes.itinerary_builder import itinerary_builder_bp
from routes.handover import handover_bp
from routes.multilingual import multilingual_bp
from routes.voice import voice_bp


load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    
    cors.init_app(
        app,
        origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Cache-Control", "X-Requested-With", "Pragma"],
        supports_credentials=True
    )

    # Initialize other extensions
    swagger.init_app(app)
    db.init_app(app)
    bcrypt.init_app(app)

    # Register blueprints
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(admin_auth_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(itinerary_admin_bp)  # Already has /api/admin/itineraries prefix
    app.register_blueprint(bookings_bp)  # Already has /api/bookings prefix
    app.register_blueprint(itinerary_builder_bp, url_prefix="/api")
    app.register_blueprint(handover_bp, url_prefix="/api")
    app.register_blueprint(multilingual_bp, url_prefix="/api")
    app.register_blueprint(voice_bp, url_prefix="/api")

    # Health check endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        """
        Health check endpoint
        ---
        tags:
          - System
        responses:
          200:
            description: System is healthy
        """
        return jsonify({
            "status": "healthy",
            "service": "Nambi Chatbot API",
            "version": "1.0.0"
        }), 200

    return app

app = create_app()

# Fetch site content before starting the server
with app.app_context():
    from routes.chat import load_site_content
    load_site_content()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
