from flask import Blueprint, request, jsonify, Response, current_app
from .services.redeem import do_redeem
from .services.rate_limit import has_jti
import jwt

bp = Blueprint('api', __name__)

@bp.post('/redeem')
def redeem():
    return do_redeem()

@bp.get('/content/<int:content_id>')
def content(content_id: int):
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'missing_token'}), 401
    token = auth.split(' ')[1]
    try:
        pub = current_app.config.get('JWT_PUBLIC_KEY')
        alg = current_app.config.get('JWT_ALG', 'RS256')
        payload = jwt.decode(token, pub, algorithms=[alg])
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'expired'}), 401
    except Exception:
        return jsonify({'error': 'invalid'}), 401

    if not has_jti(payload.get('jti','')):
        return jsonify({'error': 'revoked'}), 403
    if int(payload.get('content_id', -1)) != content_id:
        return jsonify({'error': 'wrong_content'}), 403

    return Response(f"<html><body>Protected content {content_id}</body></html>", mimetype='text/html', headers={'Cache-Control':'no-store'})

@bp.post('/decode')
def decode_qr():
    # Accept multipart/form-data with file field 'image'
    if 'image' not in request.files:
        return jsonify({'error': 'missing_file'}), 400
    file = request.files['image']
    data = file.read()
    if not data:
        return jsonify({'error': 'empty_file'}), 400
    try:
        import numpy as np
        import cv2
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'bad_image'}), 400
        detector = cv2.QRCodeDetector()
        val, points, _ = detector.detectAndDecode(img)
        if not val:
            return jsonify({'ok': False})
        return jsonify({'ok': True, 'raw': val})
    except Exception as e:
        return jsonify({'error': 'decode_failed', 'detail': str(e)}), 500
