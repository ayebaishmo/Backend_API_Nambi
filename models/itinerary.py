from extensions import db

class Itinerary(db.Model):
    __tablename__ = "itineraries"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150), nullable=False)
    days = db.Column(db.Integer, nullable=False)
    budget = db.Column(db.String(120), nullable=False)

    places = db.Column(db.Text, nullable=False)       
    accommodation = db.Column(db.Text, nullable=False)
    transport = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text, nullable=False)

    package_name = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

