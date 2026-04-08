from app import create_app
from extensions import db
from models.admin import Admin
from models.itinerary import Itinerary
from models.booking import Booking
from models.conversation import Conversation
from models.message import Message
from models.feedback import Feedback

app = create_app()

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Database tables created successfully!")
