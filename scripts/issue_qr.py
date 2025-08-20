import os
import sys
import json
import base64
import requests

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
ADMIN_API_KEY = os.environ.get('ADMIN_API_KEY') or os.environ.get('QR_ADMIN_KEY')

if not ADMIN_API_KEY:
    print('Missing ADMIN_API_KEY (or QR_ADMIN_KEY) in env')
    sys.exit(1)

merchant_id = int(os.environ.get('QR_MERCHANT_ID', '1'))
product_id = int(os.environ.get('QR_PRODUCT_ID', '1'))
duration_min = int(os.environ.get('QR_DURATION_MIN', os.environ.get('DURATION_MIN', '15')))

payload = {
    'merchant_id': merchant_id,
    'product_id': product_id,
    'duration_min': duration_min,
}

headers = {'X-Admin-Key': ADMIN_API_KEY}

# If WANT_PNG=1, request image directly
if os.environ.get('WANT_PNG', '0') == '1':
    r = requests.post(f"{BASE_URL}/admin/issue-qr", headers={**headers, 'Accept':'image/png'}, json=payload)
    if r.status_code != 200:
        print('Error:', r.status_code, r.text)
        sys.exit(1)
    out = os.environ.get('OUT', 'qr.png')
    with open(out, 'wb') as f:
        f.write(r.content)
    print('PNG saved to', out)
    sys.exit(0)

# Default: JSON mode
r = requests.post(f"{BASE_URL}/admin/issue-qr", headers=headers, json=payload)
if r.status_code != 200:
    print('Error:', r.status_code, r.text)
    sys.exit(1)
res = r.json()
print('redeem_url:', res['redeem_url'])
if 'qr_png_b64' in res:
    out = os.environ.get('OUT', 'qr.png')
    with open(out, 'wb') as f:
        f.write(base64.b64decode(res['qr_png_b64']))
    print('PNG saved to', out)
