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
