from flask import Blueprint, render_template, request
from .services.device import fingerprint_device

bp = Blueprint('public', __name__)

@bp.get('/')
def home():
    return render_template('page_public.html')

@bp.get('/redeem')
def redeem_page():
    opaque = request.args.get('c','')
    device_id, resp_cookie = fingerprint_device()
    return render_template('redeem.html', opaque=opaque, device_id=device_id)
