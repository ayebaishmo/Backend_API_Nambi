from flask import Flask
from extensions import cors, swagger, db, bcrypt
from routes.chat import chat_bp
from routes.admin_auth import admin_auth_bp
from routes.admin_login import admin_bp
from routes.itinerary_admin import itinerary_admin_bp



def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    cors.init_app(app)
    swagger.init_app(app)
    db.init_app(app)

    bcrypt.init_app(app)

    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(admin_auth_bp, url_prefix="/api")

    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(itinerary_admin_bp, url_prefix="/api")

 


    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
