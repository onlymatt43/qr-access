#!/usr/bin/env python3
import sys, base64, hmac, hashlib, time

# Usage: python scripts/check_codes.py <OPAQUE> <MERCHANT_SALT>
# Decodes our opaque token format and validates signature + staleness

def err(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)

if len(sys.argv) < 3:
    err("Usage: check_codes.py <OPAQUE> <MERCHANT_SALT>")

opaque = sys.argv[1].strip()
merchant_salt = sys.argv[2].strip().encode()

try:
    raw = base64.urlsafe_b64decode(opaque + '==')
except Exception as e:
    err(f"base64 decode: {e}")

if len(raw) < 33:
    err("too short")

msg, sig = raw[:-32], raw[-32:]
exp_sig = hmac.new(merchant_salt, msg, hashlib.sha256).digest()
if not hmac.compare_digest(sig, exp_sig):
    err("bad signature")

try:
    code_id_s, merchant_id_s, ts_s = msg.decode().split('.')
    code_id, merchant_id, ts = int(code_id_s), int(merchant_id_s), int(ts_s)
except Exception as e:
    err(f"parse: {e}")

age = int(time.time()) - ts
stale = age > 86400
print({
    'code_id': code_id,
    'merchant_id': merchant_id,
    'ts': ts,
    'age_s': age,
    'stale_>1d': stale,
})
