# SPEC-1-Accès QR temporisé (Achat → Accès → Ouverture) – Squelette de projet

## Arborescence
```
qr-access/
  app/
    __init__.py
    config.py
    models.py
    routes_public.py
    routes_api.py
    routes_admin.py
    services/
      __init__.py
      qr.py
      tokens.py
      device.py
      storage.py
      rate_limit.py
  migrations/
  static/
  templates/
  tests/
  requirements.txt
  render.yaml
```

## Fichiers clés
### requirements.txt
```
Flask>=3.0,<4.0
gunicorn
itsdangerous>=2.2
PyJWT>=2.8
psycopg2-binary
SQLAlchemy>=2.0
alembic
redis>=5.0
qrcode[pil]
python-dotenv
requests
``` 

### app/config.py
```python
import os
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.getenv('REDIS_URL')
    JWT_PRIVATE_KEY = os.getenv('JWT_PRIVATE_KEY')
    JWT_ALGORITHM = 'RS256'
    MERCHANT_SALT = os.getenv('MERCHANT_SALT')
    BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')
```

### app/services/device.py
```python
import hashlib, os, uuid
from flask import request

def fingerprint_device():
    ua = request.headers.get('User-Agent', '')
    tz = request.args.get('tz', '')
    platform = request.args.get('platform', '')
    cookie_id = request.cookies.get('dev_id') or str(uuid.uuid4())
    raw = f"{ua}|{tz}|{platform}|{cookie_id}"
    return hashlib.sha256(raw.encode()).hexdigest(), cookie_id
```

### app/services/qr.py
```python
import hmac, hashlib, base64, time
from flask import current_app as app

def make_opaque(code_id:int, merchant_id:int, ts:int=None):
    ts = ts or int(time.time())
    msg = f"{code_id}.{merchant_id}.{ts}".encode()
    sig = hmac.new(app.config['MERCHANT_SALT'].encode(), msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(msg+sig).rstrip(b'=').decode()

def verify_opaque(opaque:str):
    try:
        data = base64.urlsafe_b64decode(opaque + '==')
        parts, sig = data[:-32], data[-32:]
        expected = hmac.new(app.config['MERCHANT_SALT'].encode(), parts, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        code_id, merchant_id, ts = parts.decode().split('.')
        return int(code_id), int(merchant_id), int(ts)
    except Exception:
        return None
```

### app/routes_api.py
```python
from flask import Blueprint, request, jsonify
from .services.device import fingerprint_device
from .services.qr import verify_opaque
import uuid, time

bp = Blueprint('api', __name__)

@bp.post('/api/redeem')
def redeem():
    data = request.get_json()
    opaque = data.get('opaque')
    device_id, cookie_id = fingerprint_device()
    resolved = verify_opaque(opaque)
    if not resolved:
        return jsonify({'error': 'invalid_qr'}), 400
    code_id, merchant_id, ts = resolved
    # TODO: rate limit, bind device, issue JWT, save session in Redis
    return jsonify({'token': 'jwt_here', 'expires_at': time.time()+900})
```

## render.yaml
```yaml
services:
- type: web
  name: qr-access-flask
  env: python
  plan: starter
  buildCommand: pip install -r requirements.txt
  startCommand: gunicorn 'app:create_app()'
  envVars:
  - key: DATABASE_URL
    fromDatabase: { name: qr-access-db, property: connectionString }
  - key: REDIS_URL
    fromService: { name: qr-access-redis, type: redis }
  - key: JWT_PRIVATE_KEY
    sync: false
  - key: MERCHANT_SALT
    sync: false
  - key: BASE_URL
    value: https://yourdomain
- type: worker
  name: hls-packager
  env: docker
  plan: starter
  dockerfilePath: packager/Dockerfile

databases:
- name: qr-access-db

redis:
- name: qr-access-redis
  plan: starter
```

## Étapes suivantes
1. Compléter `redeem()` avec vérification DB/Redis + génération JWT RS256.
2. Implémenter `/fragment/<slug>`, `/media/<id>`, `/hls/<id>/*` avec proxy et contrôle JWT.
3. Construire admin minimal pour importer QR et consulter journaux.
4. Packager HLS côté worker et tester le flux complet.
5. QA sécurité (anti-rejeu, rate limit, CSP, TLS).

Avec ce squelette, l’équipe peut coder directement et déployer sur Render.

