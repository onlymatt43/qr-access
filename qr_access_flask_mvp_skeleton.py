# repo: qr-access-flask
# ├─ app/
# │  ├─ __init__.py
# │  ├─ config.py
# │  ├─ models.py
# │  ├─ routes_public.py
# │  ├─ routes_api.py
# │  ├─ routes_admin.py
# │  ├─ services/
# │  │  ├─ tokens.py
# │  │  ├─ redeem.py
# │  │  ├─ rate_limit.py
# │  │  ├─ device.py
# │  │  ├─ storage.py
# │  │  └─ qr.py
# │  ├─ templates/
# │  │  ├─ base.html
# │  │  ├─ redeem.html
# │  │  └─ page_public.html
# │  └─ static/
# ├─ migrations/ (init later)
# ├─ workers/
# │  └─ hls_packager.py
# ├─ requirements.txt
# ├─ render.yaml
# ├─ .env.example
# └─ README.md

# ===================== app/__init__.py =====================
from flask import Flask
from .config import Config
from .models import db
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config())
    db.init_app(app)

    with app.app_context():
        # defer migrations to Alembic; for quickstart only:
        db.create_all()

    from .routes_public import bp as public_bp
    from .routes_api import bp as api_bp
    from .routes_admin import bp as admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.get('/health')
    def health():
        return {'ok': True}

    return app

# ===================== app/config.py =====================
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_PRIVATE_KEY = os.environ.get('JWT_PRIVATE_KEY', 'dev')
    JWT_ALG = 'RS256'
    MERCHANT_SALT = os.environ.get('MERCHANT_SALT', 'salt')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
    HLS_SEGMENT_DURATION = int(os.environ.get('HLS_SEGMENT_DURATION', '6'))

# ===================== app/models.py =====================
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()

class Merchant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True)
    contact_url = db.Column(db.Text)
    webhook_url = db.Column(db.Text)
    status = db.Column(db.String(32), default='active')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url_or_blob_ref = db.Column(db.Text, nullable=False)
    mime_type = db.Column(db.String(128))
    type = db.Column(db.String(32), default='page')  # page|fragment|media
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchant.id'))
    name = db.Column(db.String(255), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'))
    default_duration_min = db.Column(db.Integer, nullable=False)
    policy_one_device = db.Column(db.Boolean, default=True)

class Code(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchant.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    code_hash = db.Column(db.Text, nullable=False, unique=True)
    batch_id = db.Column(db.String(64))
    duration_min = db.Column(db.Integer)
    issued_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    expires_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(32), default='issued')

class Redemption(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)
    code_id = db.Column(db.BigInteger, db.ForeignKey('code.id'))
    device_id = db.Column(db.String(64))
    first_redeemed_at = db.Column(db.DateTime(timezone=True))
    last_seen_at = db.Column(db.DateTime(timezone=True))
    access_jwt_id = db.Column(db.String(64))
    ip_first = db.Column(db.String(64))
    user_agent_first = db.Column(db.Text)

class AuditLog(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)
    ts = db.Column(db.DateTime(timezone=True), server_default=func.now())
    actor_type = db.Column(db.String(32))
    actor_id = db.Column(db.String(64))
    event_type = db.Column(db.String(64))
    payload_json = db.Column(db.JSON)

# ===================== app/services/tokens.py =====================
import time, jwt, hmac, hashlib, base64
from flask import current_app

# Opaque QR token (HMAC)
def make_opaque(code_id: int, merchant_id: int, ts: int|None=None) -> str:
    if ts is None:
        ts = int(time.time())
    msg = f"{code_id}.{merchant_id}.{ts}".encode()
    secret = current_app.config['MERCHANT_SALT'].encode()
    sig = hmac.new(secret, msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(msg + sig).rstrip(b'=').decode()

def resolve_opaque(b64: str):
    data = base64.urlsafe_b64decode(b64 + '==')
    msg, sig = data[:-32], data[-32:]
    secret = current_app.config['MERCHANT_SALT'].encode()
    exp_sig = hmac.new(secret, msg, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, exp_sig):
        raise ValueError('bad signature')
    parts = msg.decode().split('.')
    code_id, merchant_id, ts = int(parts[0]), int(parts[1]), int(parts[2])
    # optional: enforce staleness window, e.g., 24h
    if time.time() - ts > 86400:
        raise ValueError('stale')
    return code_id, merchant_id, ts

# Access JWT (RS256)
def sign_access_jwt(sub_code_id: int, jti: str, exp_ts: int, merchant_id: int, device_id: str, content_id: int) -> str:
    payload = {
        'sub': str(sub_code_id),
        'jti': jti,
        'exp': exp_ts,
        'merchant_id': merchant_id,
        'device_id': device_id,
        'content_id': content_id,
    }
    key = current_app.config['JWT_PRIVATE_KEY']
    return jwt.encode(payload, key, algorithm=current_app.config['JWT_ALG'])

# ===================== app/services/rate_limit.py =====================
import time, json
import redis
from flask import current_app

_r = None

def r():
    global _r
    if _r is None:
        _r = redis.from_url(current_app.config['REDIS_URL'], decode_responses=True)
    return _r

def check_rate_ip(ip: str, limit=20, window=60):
    k = f"rl:ip:{ip}:{int(time.time()//window)}"
    v = r().incr(k)
    r().expire(k, window)
    if v > limit:
        raise ValueError('rate exceeded')

# anti-replay jti

def remember_jti(jti: str, ttl: int):
    r().setex(f"jti:{jti}", ttl, '1')

def has_jti(jti: str) -> bool:
    return r().exists(f"jti:{jti}") == 1

# session per code_id

def save_session(code_id: int, device_id: str, jti: str, exp_ts: int):
    ttl = max(0, exp_ts - int(time.time()) + 60)
    r().setex(f"sess:{code_id}", ttl, json.dumps({'device_id': device_id, 'jti': jti, 'exp': exp_ts}))

def load_session(code_id: int):
    raw = r().get(f"sess:{code_id}")
    return json.loads(raw) if raw else None

# ===================== app/services/device.py =====================
import hashlib, os
from flask import request

def fingerprint_device() -> tuple[str, tuple|None]:
    ua = request.headers.get('User-Agent','')
    tz = request.headers.get('Sec-CH-Timezone','') or request.args.get('tz','')
    plat = request.headers.get('Sec-CH-UA-Platform','') or request.args.get('platform','')
    lang = request.headers.get('Accept-Language','')
    entropy = request.cookies.get('did') or os.urandom(8).hex()
    raw = f"{ua}|{tz}|{plat}|{lang}|{entropy}"
    did = hashlib.sha256(raw.encode()).hexdigest()[:32]
    resp_cookie = None if request.cookies.get('did') else ('did', entropy, {'httponly':True, 'samesite':'Lax', 'secure':True, 'max_age':31536000})
    return did, resp_cookie

# ===================== app/services/storage.py =====================
# Minimal stub: replace with S3/Cloud storage SDK
from flask import Response

def stream_bytes(iterable, headers: dict):
    return Response(iterable, headers=headers)

# ===================== app/services/qr.py =====================
import qrcode

def make_qr(url: str, path: str):
    img = qrcode.make(url)
    img.save(path)

# ===================== app/services/redeem.py =====================
import time, uuid
from flask import request, jsonify
from .tokens import resolve_opaque, sign_access_jwt
from .rate_limit import check_rate_ip, save_session, remember_jti
from ..models import db, Code, Redemption, Product, Content


def do_redeem():
    data = request.get_json()
    opaque = data.get('opaque')
    device_id = data.get('device_id')
    ip = request.remote_addr
    check_rate_ip(ip)

    code_id, merchant_id, ts = resolve_opaque(opaque)
    code = Code.query.get(code_id)
    if not code or code.status != 'issued':
        return jsonify({'error': 'invalid_code'}), 400

    red = Redemption.query.filter_by(code_id=code.id).first()
    if red is None:
        red = Redemption(code_id=code.id, device_id=device_id, ip_first=ip, user_agent_first=request.headers.get('User-Agent'))
        db.session.add(red)
    elif red.device_id != device_id:
        return jsonify({'error': 'device_mismatch'}), 403

    prod = Product.query.get(code.product_id)
    content = Content.query.get(prod.content_id)

    duration_min = code.duration_min or prod.default_duration_min
    exp_ts = int(time.time()) + duration_min * 60
    jti = uuid.uuid4().hex

    token = sign_access_jwt(code.id, jti, exp_ts, code.merchant_id, device_id, content.id)
    save_session(code.id, device_id, jti, exp_ts)
    remember_jti(jti, duration_min * 60 + 60)

    red.first_redeemed_at = red.first_redeemed_at or db.func.now()
    red.last_seen_at = db.func.now()
    red.access_jwt_id = jti
    db.session.commit()

    return jsonify({'token': token, 'expires_at': exp_ts, 'content_id': content.id})

# ===================== app/routes_public.py =====================
from flask import Blueprint, render_template, request
from .services.device import fingerprint_device

bp = Blueprint('public', __name__)

@bp.get('/')
def home():
    return render_template('page_public.html')

@bp.get('/redeem')
def redeem_page():
    opaque = request.args.get('c','')
    device_id, resp_cookie = fingerprint_device()
    return render_template('redeem.html', opaque=opaque, device_id=device_id)

# ===================== app/routes_api.py =====================
from flask import Blueprint, request
from .services.redeem import do_redeem
from .services.rate_limit import has_jti, load_session
from flask import jsonify, Response

bp = Blueprint('api', __name__)

@bp.post('/redeem')
def redeem():
    return do_redeem()

@bp.get('/content/<int:content_id>')
def content(content_id: int):
    # Example protected resource (replace with proxy to real HTML/fragment)
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'missing_token'}), 401
    # Validate token on edge: jti present in Redis session
    # (Full JWT validation should be added here)
    return Response(f"<html><body>Protected content {content_id}</body></html>", mimetype='text/html', headers={'Cache-Control':'no-store'})

# ===================== app/routes_admin.py =====================
from flask import Blueprint, jsonify

bp = Blueprint('admin', __name__)

@bp.get('/ping')
def ping():
    return jsonify({'admin': 'ok'})

# ===================== app/templates/base.html =====================
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title or 'QR Access' }}</title>
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data:; media-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" />
</head>
<body>
  {% block body %}{% endblock %}
</body>
</html>

# ===================== app/templates/page_public.html =====================
{% extends 'base.html' %}
{% block body %}
<h1>Page publique</h1>
<p>Scannez votre QR pour accéder au contenu protégé.</p>
<a href="/redeem">Aller au scan</a>
{% endblock %}

# ===================== app/templates/redeem.html =====================
{% extends 'base.html' %}
{% block body %}
<h1>Validation QR</h1>
<input type="hidden" id="opaque" value="{{ opaque }}" />
<input type="hidden" id="device_id" value="{{ device_id }}" />
<button id="btn-scan">Scanner QR</button>
<input id="file" type="file" accept="image/*" capture="environment" style="display:none" />
<pre id="log"></pre>
<script>
const opaqueInUrl = document.getElementById('opaque').value;
const deviceId = document.getElementById('device_id').value;
const log = (m)=>document.getElementById('log').textContent += m+'\n';

async function redeem(opaque){
  const r = await fetch('/api/redeem', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({opaque, device_id: deviceId})});
  const data = await r.json();
  if(!r.ok){ log('Erreur: '+JSON.stringify(data)); return; }
  log('OK, token reçu, ouverture du contenu '+data.content_id);
  const rr = await fetch('/content/'+data.content_id, {headers:{'Authorization':'Bearer '+data.token}});
  document.body.innerHTML = await rr.text();
}

// If opaque already in URL, try directly
if (opaqueInUrl) redeem(opaqueInUrl);

document.getElementById('btn-scan').onclick = async ()=>{
  // Minimal fallback: open file picker to upload QR image (for MVP)
  document.getElementById('file').click();
};

document.getElementById('file').addEventListener('change', async (e)=>{
  log('Image sélectionnée. (Décodage QR côté serveur à implémenter si nécessaire)');
  // For MVP we assume opaque comes via URL; decoder can be added later.
});
</script>
{% endblock %}

# ===================== workers/hls_packager.py =====================
# Placeholder worker – replace with actual ffmpeg calls on uploaded assets.
print('hls-packager worker placeholder')

# ===================== requirements.txt =====================
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
user-agents

# ===================== render.yaml =====================
services:
- type: web
  name: qr-access-flask
  env: python
  plan: starter
  buildCommand: pip install -r requirements.txt
  startCommand: gunicorn 'app:create_app()'
  envVars:
  - key: DATABASE_URL
    value: sqlite:///local.db
  - key: REDIS_URL
    value: redis://localhost:6379/0
  - key: JWT_PRIVATE_KEY
    sync: false
  - key: MERCHANT_SALT
    value: dev-secret
  - key: BASE_URL
    value: http://localhost:5000

# ===================== .env.example =====================
SECRET_KEY=dev
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://:pass@host:6379/0
JWT_PRIVATE_KEY="""-----BEGIN PRIVATE KEY-----
...PEM...
-----END PRIVATE KEY-----"""
MERCHANT_SALT=change-me
BASE_URL=https://yourdomain

# ===================== README.md =====================
# QR Access Flask MVP

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app:create_app
flask run
```

## Notes
- Le flux `/redeem` retourne un JWT d’accès et un `content_id`.
- L’endpoint `/content/<id>` est un stub : ajoutez la **validation complète du JWT** (clé publique) et remplacez par le **proxy réel** (fragments/médias/HLS).
- Ajoutez Alembic pour les migrations et l’intégration Render (Postgres/Redis) selon votre environnement.
