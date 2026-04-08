from datetime import datetime, timedelta

class ItineraryValidator:
    """Validate itinerary constraints and feasibility"""
    
    # Budget ranges per tier (USD per day)
    BUDGET_RANGES = {
        'budget': (30, 100),
        'mid-range': (100, 250),
        'luxury': (250, 1000),
        'ultra-luxury': (1000, 5000)
    }
    
    # Travel times between major destinations (hours)
    TRAVEL_TIMES = {
        ('Kampala', 'Entebbe'): 1,
        ('Kampala', 'Jinja'): 2,
        ('Kampala', 'Murchison Falls'): 5,
        ('Kampala', 'Queen Elizabeth'): 6,
        ('Kampala', 'Bwindi'): 8,
        ('Kampala', 'Kidepo'): 10,
        ('Entebbe', 'Jinja'): 2.5,
        ('Jinja', 'Murchison Falls'): 6,
        ('Queen Elizabeth', 'Bwindi'): 4,
    }
    
    # Seasonal restrictions (month ranges)
    WET_SEASON_MONTHS = [3, 4, 5, 9, 10, 11]  # March-May, Sept-Nov
    
    @staticmethod
    def validate_duration(days):
        """Validate trip duration"""
        errors = []
        if days < 1:
            errors.append("Trip duration must be at least 1 day")
        if days > 30:
            errors.append("Trip duration cannot exceed 30 days")
        return errors
    
    @staticmethod
    def validate_budget(budget_str, days):
        """Validate budget against duration and tier"""
        errors = []
        
        try:
            # Extract numeric value if budget is a string like "$500" or "500 USD"
            budget_value = float(''.join(filter(str.isdigit, budget_str)))
            
            if budget_value <= 0:
                errors.append("Budget must be greater than 0")
            
            # Check if budget is realistic for duration
            min_budget = days * 30  # Minimum $30/day
            if budget_value < min_budget:
                errors.append(f"Budget too low for {days} days. Minimum recommended: ${min_budget}")
            
        except (ValueError, TypeError):
            errors.append("Invalid budget format")
        
        return errors
    
    @staticmethod
    def validate_route_feasibility(places_str, days):
        """Validate if route is feasible within given days"""
        errors = []
        warnings = []
        
        # Parse places
        places = [p.strip() for p in places_str.split(',') if p.strip()]
        
        if len(places) < 1:
            errors.append("At least one destination is required")
            return errors, warnings
        
        # Calculate total travel time
        total_travel_hours = 0
        for i in range(len(places) - 1):
            origin = places[i]
            destination = places[i + 1]
            
            # Check both directions
            travel_time = ItineraryValidator.TRAVEL_TIMES.get(
                (origin, destination),
                ItineraryValidator.TRAVEL_TIMES.get((destination, origin), 0)
            )
            
            total_travel_hours += travel_time
        
        # Estimate travel days (8 hours = 1 day)
        travel_days = total_travel_hours / 8
        activity_days = days - travel_days
        
        if activity_days < 1:
            errors.append(f"Too many destinations for {days} days. Estimated {travel_days:.1f} days just for travel")
        elif activity_days < len(places):
            warnings.append(f"Tight schedule: Only {activity_days:.1f} days for activities across {len(places)} destinations")
        
        # Check for too many destinations
        if len(places) > days:
            warnings.append(f"Visiting {len(places)} destinations in {days} days may be rushed")
        
        return errors, warnings
    
    @staticmethod
    def check_seasonal_considerations(start_date_str=None):
        """Check seasonal travel considerations"""
        warnings = []
        
        if not start_date_str:
            return warnings
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            month = start_date.month
            
            if month in ItineraryValidator.WET_SEASON_MONTHS:
                warnings.append(f"Travel in {start_date.strftime('%B')} is during wet season. Roads may be challenging, but great for birding!")
            
        except ValueError:
            pass  # Invalid date format, skip check
        
        return warnings
    
    @staticmethod
    def validate_complete_itinerary(data):
        """Complete validation of itinerary data"""
        errors = []
        warnings = []
        
        days = data.get('days', 0)
        budget = data.get('budget', '')
        places = data.get('places', '')
        start_date = data.get('start_date')
        
        # Validate duration
        errors.extend(ItineraryValidator.validate_duration(days))
        
        # Validate budget
        errors.extend(ItineraryValidator.validate_budget(budget, days))
        
        # Validate route
        route_errors, route_warnings = ItineraryValidator.validate_route_feasibility(places, days)
        errors.extend(route_errors)
        warnings.extend(route_warnings)
        
        # Check seasonal considerations
        warnings.extend(ItineraryValidator.check_seasonal_considerations(start_date))
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
