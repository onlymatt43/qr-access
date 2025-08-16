from flask import Blueprint, jsonify

bp = Blueprint('admin', __name__)

@bp.get('/ping')
def ping():
    return jsonify({'admin': 'ok'})
