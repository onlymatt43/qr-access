import os
import json
import pathlib
import sys

# Ensure project root is on PYTHONPATH
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Minimal env for test (set before importing app so Config reads them)
os.environ.setdefault('ADMIN_API_KEY', 'test-key')
os.environ.setdefault('BASE_URL', 'http://localhost:5000')
os.environ.setdefault('MERCHANT_SALT', 'salt-for-test')

from app import create_app

app = create_app()

with app.app_context():
    client = app.test_client()

    # 1) Unauthorized
    r = client.post('/admin/issue-qr', json={'merchant_id': 1, 'product_id': 1, 'duration_min': 15})
    print('unauthorized_status', r.status_code)

    # 2) Authorized JSON
    r = client.post('/admin/issue-qr', headers={'X-Admin-Key': 'test-key', 'Accept': 'application/json'}, json={'merchant_id': 1, 'product_id': 1, 'duration_min': 15})
    print('json_status', r.status_code)
    try:
        data = r.get_json()
        print('json_keys', sorted(list(data.keys())))
    except Exception as e:
        print('json_parse_error', e)
        print('body', r.data[:200])

    # 3) Authorized PNG
    r = client.post('/admin/issue-qr', headers={'X-Admin-Key': 'test-key', 'Accept': 'image/png'}, json={'merchant_id': 1, 'product_id': 1, 'duration_min': 15})
    print('png_status', r.status_code, 'mimetype', r.mimetype, 'len', len(r.data))
