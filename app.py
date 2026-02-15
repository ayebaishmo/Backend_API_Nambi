import os
from flask import Flask
from dotenv import load_dotenv
from extensions import cors, swagger, db, bcrypt
from routes.chat import chat_bp
from routes.admin_auth import admin_auth_bp
from routes.admin_login import admin_bp
from routes.itinerary_admin import itinerary_admin_bp


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
    app.register_blueprint(itinerary_admin_bp, url_prefix="/api")

    return app

app = create_app()

# Fetch site content before starting the server
with app.app_context():
    from routes.chat import load_site_content
    load_site_content()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
