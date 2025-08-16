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
