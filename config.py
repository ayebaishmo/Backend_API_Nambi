import os
from urllib.parse import unquote

class Config:
    # Get DATABASE_URL and decode any URL-encoded characters
    database_url = os.getenv("DATABASE_URL")
    
    # Debug: print what we got
    print(f"DEBUG: Raw DATABASE_URL from env: {database_url}")
    
    if database_url:
        # Decode URL-encoded characters in the password
        SQLALCHEMY_DATABASE_URI = unquote(database_url)
        print(f"DEBUG: Decoded DATABASE_URL: {SQLALCHEMY_DATABASE_URI}")
    else:
        SQLALCHEMY_DATABASE_URI = None
        print("DEBUG: DATABASE_URL is None!")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
