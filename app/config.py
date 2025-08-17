import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_PRIVATE_KEY = os.environ.get('JWT_PRIVATE_KEY')
    JWT_PUBLIC_KEY = os.environ.get('JWT_PUBLIC_KEY')
    JWT_ALG = 'RS256'
    MERCHANT_SALT = os.environ.get('MERCHANT_SALT', 'salt')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
    HLS_SEGMENT_DURATION = int(os.environ.get('HLS_SEGMENT_DURATION', '6'))

    def __init__(self):
        # Fallback: load keys from local files if env vars absent
        if not self.JWT_PRIVATE_KEY:
            try:
                with open('jwt.key', 'r') as f:
                    self.JWT_PRIVATE_KEY = f.read()
            except Exception:
                pass
        if not self.JWT_PUBLIC_KEY:
            try:
                with open('jwt.pub', 'r') as f:
                    self.JWT_PUBLIC_KEY = f.read()
            except Exception:
                pass
