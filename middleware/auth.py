from functools import wraps
from flask import request, jsonify
import jwt
import os
from datetime import datetime, timedelta

def generate_token(admin_id):
    """Generate JWT token for admin"""
    payload = {
        'admin_id': admin_id,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, os.getenv('JWT_SECRET_KEY'), algorithm='HS256')

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
        return payload['admin_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Decorator to protect admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        admin_id = verify_token(token)
        if not admin_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        request.admin_id = admin_id
        return f(*args, **kwargs)
    
    return decorated_function
