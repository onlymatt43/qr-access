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
    ADMIN_API_KEY = os.environ.get('ADMIN_API_KEY')

    def __init__(self):
        # Optional fallbacks to support Secret Files on Render (/etc/secrets)
        if not self.JWT_PRIVATE_KEY:
            for p in ('/etc/secrets/jwt.key', 'jwt.key'):
                try:
                    with open(p, 'r') as f:
                        self.JWT_PRIVATE_KEY = f.read().strip()
                        break
                except Exception:
                    continue
        if not self.JWT_PUBLIC_KEY:
            for p in ('/etc/secrets/jwt.pub', 'jwt.pub'):
                try:
                    with open(p, 'r') as f:
                        self.JWT_PUBLIC_KEY = f.read().strip()
                        break
                except Exception:
                    continue
        # Optional fallbacks for other secrets
        if (not self.SECRET_KEY) or self.SECRET_KEY == 'dev':
            try:
                with open('/etc/secrets/secret_key', 'r') as f:
                    self.SECRET_KEY = f.read().strip()
            except Exception:
                pass
        if (not self.MERCHANT_SALT) or self.MERCHANT_SALT == 'salt':
            try:
                with open('/etc/secrets/merchant_salt', 'r') as f:
                    self.MERCHANT_SALT = f.read().strip()
            except Exception:
                pass
