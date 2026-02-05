from flask import Flask
from extensions import cors, swagger
from routes.chat import chat_bp

def create_app():
    app = Flask(__name__)

    cors.init_app(app)
    swagger.init_app(app)

    app.register_blueprint(chat_bp, url_prefix="/api")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
