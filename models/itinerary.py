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
    
    # Validation constants
    MIN_DAYS = 1
    MAX_DAYS = 30
    
    @classmethod
    def validate_itinerary_data(cls, days, budget, places):
        """Validate itinerary data before creation/update"""
        errors = []
        
        # Validate days
        if days < cls.MIN_DAYS or days > cls.MAX_DAYS:
            errors.append(f"Days must be between {cls.MIN_DAYS} and {cls.MAX_DAYS}")
        
        # Validate budget
        if not budget or budget.strip() == "":
            errors.append("Budget is required")
        
        # Validate places
        if not places or places.strip() == "":
            errors.append("Places/destinations are required")
        
        return errors

