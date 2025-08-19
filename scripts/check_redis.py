#!/usr/bin/env python3
import sys, json, redis

# Usage: python scripts/check_redis.py <REDIS_URL> <CODE_ID> <JTI>
# Shows session for code_id and whether a jti key exists

if len(sys.argv) < 4:
    print("Usage: check_redis.py <REDIS_URL> <CODE_ID> <JTI>")
    sys.exit(1)

url = sys.argv[1].strip()
code_id = int(sys.argv[2])
jti = sys.argv[3].strip()

r = redis.from_url(url, decode_responses=True)

sess = r.get(f"sess:{code_id}")
jti_exists = r.exists(f"jti:{jti}") == 1

print(json.dumps({
    'redis': url,
    'sess_key': f'sess:{code_id}',
    'session': json.loads(sess) if sess else None,
    'jti_key': f'jti:{jti}',
    'jti_exists': jti_exists,
}, indent=2))
