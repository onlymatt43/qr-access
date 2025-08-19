import os, time, json, threading
import redis
from flask import current_app

_r = None
_lock = threading.Lock()

class _MemStore:
    def __init__(self):
        self._data = {}
        self._exp = {}
        self._lock = threading.Lock()

    def _cleanup(self):
        now = time.time()
        expired = [k for k, ts in self._exp.items() if ts <= now]
        for k in expired:
            self._data.pop(k, None)
            self._exp.pop(k, None)

    def incr(self, key):
        with self._lock:
            self._cleanup()
            v = int(self._data.get(key, '0')) + 1
            self._data[key] = str(v)
            return v

    def expire(self, key, ttl):
        with self._lock:
            self._cleanup()
            self._exp[key] = time.time() + ttl

    def setex(self, key, ttl, value):
        with self._lock:
            self._cleanup()
            self._data[key] = value
            self._exp[key] = time.time() + ttl

    def exists(self, key):
        with self._lock:
            self._cleanup()
            return 1 if key in self._data else 0

    def get(self, key):
        with self._lock:
            self._cleanup()
            return self._data.get(key)

def r():
    global _r
    if _r is not None:
        return _r
    with _lock:
        if _r is not None:
            return _r
        # Decide whether to use Redis or memory store
        use_redis = os.environ.get('USE_REDIS', '1').lower() not in ('0', 'false', 'no')
        url = current_app.config.get('REDIS_URL')
        if use_redis and url:
            try:
                client = redis.from_url(url, decode_responses=True)
                # Test connection once; fallback to memory on failure
                client.ping()
                _set(client)
                return _r
            except Exception:
                pass
        # Fallback to in-memory store
        _set(_MemStore())
        return _r

def _set(store):
    global _r
    _r = store

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
