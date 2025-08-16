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
