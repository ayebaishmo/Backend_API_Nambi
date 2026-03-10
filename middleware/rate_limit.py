from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta
from collections import defaultdict

# Simple in-memory rate limiter
rate_limit_store = defaultdict(list)
RATE_LIMIT = 10  # requests
RATE_WINDOW = 80  # seconds

def rate_limit(f):
    """Rate limiting decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get client identifier (IP address)
        client_ip = request.remote_addr
        
        # Get current time
        now = datetime.utcnow()
        
        # Clean old requests
        rate_limit_store[client_ip] = [
            req_time for req_time in rate_limit_store[client_ip]
            if now - req_time < timedelta(seconds=RATE_WINDOW)
        ]
        
        # Check rate limit
        if len(rate_limit_store[client_ip]) >= RATE_LIMIT:
            return jsonify({
                'error': f'Rate limit exceeded. Maximum {RATE_LIMIT} requests per {RATE_WINDOW} seconds.'
            }), 429
        
        # Add current request
        rate_limit_store[client_ip].append(now)
        
        return f(*args, **kwargs)
    
    return decorated_function
