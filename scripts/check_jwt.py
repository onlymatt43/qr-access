#!/usr/bin/env python3
import sys, json, jwt

# Usage: python scripts/check_jwt.py <JWT> <PUBLIC_KEY_FILE|->
# If '-' is passed, try env JWT_PUBLIC_KEY, else read jwt.pub in CWD.

def load_pubkey(path_hint: str):
    import os
    if path_hint and path_hint != '-':
        with open(path_hint, 'r') as f:
            return f.read()
    k = os.environ.get('JWT_PUBLIC_KEY')
    if k:
        return k
    try:
        with open('jwt.pub', 'r') as f:
            return f.read()
    except Exception:
        return None

if len(sys.argv) < 3:
    print("Usage: check_jwt.py <JWT> <PUBLIC_KEY_FILE|->")
    sys.exit(1)

raw = sys.argv[1].strip()
pub = load_pubkey(sys.argv[2].strip())
if not pub:
    print("ERROR: no public key available (env JWT_PUBLIC_KEY or jwt.pub)")
    sys.exit(1)

try:
    payload = jwt.decode(raw, pub, algorithms=['RS256'])
except Exception as e:
    print("ERROR:", e)
    sys.exit(1)

print(json.dumps(payload, indent=2, sort_keys=True))
