from extensions import db

class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    destination = db.Column(db.String(255), nullable=True)
    days = db.Column(db.Integer, nullable=True)
    budget = db.Column(db.Float, nullable=True)
    package = db.Column(db.String(100), nullable=True)
    message = db.Column(db.Text, nullable=True)
    session_id = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='pending')  # pending, confirmed, cancelled
    created_at = db.Column(db.DateTime, server_default=db.func.now())
