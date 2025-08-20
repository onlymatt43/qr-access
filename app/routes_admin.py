from flask import Blueprint, jsonify, request, current_app, send_file
from datetime import datetime
import io
import time
import hashlib
import base64
from .models import db, Code
from .services.tokens import make_opaque
from .services.qr import make_qr_bytes

bp = Blueprint('admin', __name__)

@bp.get('/ping')
def ping():
    return jsonify({'admin': 'ok'})

@bp.post('/issue-qr')
def issue_qr():
    # Simple API-key auth
    api_key = request.headers.get('X-Admin-Key') or request.args.get('key')
    if not api_key or api_key != (current_app.config.get('ADMIN_API_KEY') or ''):
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    merchant_id = int(data.get('merchant_id') or 1)
    product_id = int(data.get('product_id') or 1)
    duration_min = int(data.get('duration_min') or 15)

    # Create a lightweight code record
    now = datetime.utcnow()
    code_hash = hashlib.sha256(f"{merchant_id}.{product_id}.{now.timestamp()}".encode()).hexdigest()
    code = Code(
        merchant_id=merchant_id,
        product_id=product_id,
        code_hash=code_hash,
        duration_min=duration_min,
        status='issued',
    )
    db.session.add(code)
    db.session.commit()

    opaque = make_opaque(code.id, merchant_id, int(time.time()))
    redeem_url = f"{current_app.config.get('BASE_URL')}/redeem?c={opaque}"
    png = make_qr_bytes(redeem_url)

    # Return multipart-like JSON + optional binary when asked
    accept = request.headers.get('Accept','')
    if 'image/png' in accept:
        return send_file(
            io.BytesIO(png), mimetype='image/png', as_attachment=False, download_name=f"qr_{code.id}.png",
            etag=False,
        )
    return jsonify({
        'ok': True,
        'code_id': code.id,
        'redeem_url': redeem_url,
        'qr_png_b64': base64.b64encode(png).decode('ascii'),
    })
