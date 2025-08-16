import time, uuid
from flask import request, jsonify
from .tokens import resolve_opaque, sign_access_jwt
from .rate_limit import check_rate_ip, save_session, remember_jti
from ..models import db, Code, Redemption, Product, Content


def do_redeem():
    data = request.get_json() or {}
    opaque = data.get('opaque')
    device_id = data.get('device_id')
    ip = request.remote_addr or '0.0.0.0'
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
