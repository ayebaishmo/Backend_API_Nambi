from functools import wraps
from datetime import datetime, timedelta
import hashlib
import json

class CacheManager:
    """Simple in-memory cache manager (can be upgraded to Redis later)"""
    
    _cache = {}
    _cache_timestamps = {}
    
    DEFAULT_TTL = 3600  # 1 hour in seconds
    
    @staticmethod
    def get(key):
        """Get value from cache"""
        if key in CacheManager._cache:
            # Check if expired
            if CacheManager._is_expired(key):
                CacheManager.delete(key)
                return None
            return CacheManager._cache[key]
        return None
    
    @staticmethod
    def set(key, value, ttl=None):
        """Set value in cache with TTL"""
        if ttl is None:
            ttl = CacheManager.DEFAULT_TTL
        
        CacheManager._cache[key] = value
        CacheManager._cache_timestamps[key] = {
            'created_at': datetime.utcnow(),
            'ttl': ttl
        }
    
    @staticmethod
    def delete(key):
        """Delete key from cache"""
        if key in CacheManager._cache:
            del CacheManager._cache[key]
        if key in CacheManager._cache_timestamps:
            del CacheManager._cache_timestamps[key]
    
    @staticmethod
    def clear():
        """Clear all cache"""
        CacheManager._cache.clear()
        CacheManager._cache_timestamps.clear()
    
    @staticmethod
    def _is_expired(key):
        """Check if cache key is expired"""
        if key not in CacheManager._cache_timestamps:
            return True
        
        timestamp_data = CacheManager._cache_timestamps[key]
        created_at = timestamp_data['created_at']
        ttl = timestamp_data['ttl']
        
        expiry_time = created_at + timedelta(seconds=ttl)
        return datetime.utcnow() > expiry_time
    
    @staticmethod
    def cleanup_expired():
        """Remove expired cache entries"""
        expired_keys = [
            key for key in CacheManager._cache.keys()
            if CacheManager._is_expired(key)
        ]
        
        for key in expired_keys:
            CacheManager.delete(key)
        
        return len(expired_keys)
    
    @staticmethod
    def generate_key(*args, **kwargs):
        """Generate cache key from arguments"""
        key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()


def cached(ttl=None):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{CacheManager.generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = CacheManager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            CacheManager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator
