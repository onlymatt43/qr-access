# Cloud-dev setup (GitHub + Render) — avec validation JWT & proxy HLS

## TL;DR

- **Préviews PR** : un environnement temporaire par Pull Request.
- **Staging** : un environnement stable qui reçoit `main` après merge.
- Ajout : **Validation JWT complète** pour `/content` et **proxy HLS** minimal.

---

## GitHub Actions — CI/CD

`.github/workflows/ci-preview.yml`

```yaml
name: CI & Render Previews
on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: python -m pip install -r requirements.txt
      - run: python -m compileall .

  render-preview:
    if: github.event_name == 'pull_request'
    needs: ci
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Create/Update Render Preview
        uses: render-oss/action@v1
        with:
          serviceId: ${{ secrets.RENDER_SERVICE_ID }}
          apiKey: ${{ secrets.RENDER_API_KEY }}
          branch: ${{ github.head_ref }}
          pr: ${{ github.event.number }}
          envVars: |
            BRANCH=${{ github.head_ref }}
            IS_PREVIEW=true

  render-staging:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: ci
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Render Staging
        uses: render-oss/action@v1
        with:
          serviceId: ${{ secrets.RENDER_SERVICE_ID_STAGING }}
          apiKey: ${{ secrets.RENDER_API_KEY }}
          branch: main
```

---

## render.yaml — variables dynamiques

```yaml
services:
- type: web
  name: qr-access-${BRANCH:-staging}
  env: python
  plan: starter
  buildCommand: pip install -r requirements.txt
  startCommand: gunicorn 'app:create_app()'
  envVars:
  - key: DATABASE_URL
    fromDatabase: { name: qr-access-db-${BRANCH:-staging}, property: connectionString }
  - key: REDIS_URL
    fromService: { name: qr-access-redis-${BRANCH:-staging}, type: redis }
  - key: JWT_PRIVATE_KEY
    sync: false
  - key: JWT_PUBLIC_KEY
    sync: false
  - key: MERCHANT_SALT
    sync: false
  - key: BASE_URL
    value: https://qr-access-${BRANCH:-staging}.onrender.com

databases:
- name: qr-access-db-${BRANCH:-staging}

redis:
- name: qr-access-redis-${BRANCH:-staging}
  plan: starter
```

---

## Script de seed — `scripts/seed.py`

```python
import os, time
from app import create_app
from app.models import db, Merchant, Product, Content, Code
from app.services.tokens import make_opaque

app = create_app()
with app.app_context():
    m = Merchant(name='Demo', slug='demo'); db.session.add(m)
    c = Content(url_or_blob_ref='s3://bucket/private/page.html', mime_type='text/html', type='page'); db.session.add(c)
    p = Product(merchant_id=1, name='Pass 15min', content_id=1, default_duration_min=15); db.session.add(p)
    db.session.commit()

    code = Code(id=1, merchant_id=1, product_id=1, code_hash='hash:1', duration_min=15)
    db.session.add(code)
    db.session.commit()

    opaque = make_opaque(1, 1, int(time.time()))
    print('QR URL:', os.environ.get('BASE_URL','http://localhost:5000') + '/redeem?c=' + opaque)
```

---

## Validation JWT pour `/content`

Dans `routes_api.py` :

```python
import jwt, os
from flask import request, jsonify, Response, current_app
from .services.rate_limit import has_jti

@bp.get('/content/<int:content_id>')
def content(content_id: int):
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'missing_token'}), 401
    token = auth.split(' ')[1]
    try:
        pub_key = os.environ['JWT_PUBLIC_KEY']
        payload = jwt.decode(token, pub_key, algorithms=[current_app.config['JWT_ALGORITHM']])
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid'}), 401

    if has_jti(payload['jti']) is False:
        return jsonify({'error': 'revoked'}), 403
    if payload['content_id'] != content_id:
        return jsonify({'error': 'wrong_content'}), 403

    return Response(f"<html><body>Protected content {content_id}</body></html>", mimetype='text/html', headers={'Cache-Control':'no-store'})
```

---

## Proxy HLS minimal

```python
@bp.get('/hls/<int:content_id>/<path:filename>')
def hls_proxy(content_id: int, filename: str):
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'missing_token'}), 401
    token = auth.split(' ')[1]
    pub_key = os.environ['JWT_PUBLIC_KEY']
    try:
        payload = jwt.decode(token, pub_key, algorithms=[current_app.config['JWT_ALGORITHM']])
    except Exception:
        return jsonify({'error': 'invalid_token'}), 401

    if payload['content_id'] != content_id:
        return jsonify({'error': 'wrong_content'}), 403

    # TODO: fetch from storage provider
    # Example: open local file (m3u8/ts) and stream
    local_path = f"/mnt/private_hls/{content_id}/{filename}"
    if not os.path.exists(local_path):
        return jsonify({'error': 'not_found'}), 404
    def generate():
        with open(local_path, 'rb') as f:
            while chunk := f.read(8192):
                yield chunk
    return Response(generate(), headers={'Cache-Control': 'no-store', 'Content-Type': 'application/vnd.apple.mpegurl' if filename.endswith('.m3u8') else 'video/MP2T'})
```

---

## Tests réels

1. PR → Preview Render.
2. `python scripts/seed.py` → récupère QR URL.
3. Scanner QR → reçoit JWT.
4. `/content/<id>` → retourne HTML protégé si JWT OK.
5. `/hls/<id>/master.m3u8` → retourne playlist si JWT OK.
6. Expiration → 401 + redirection marchand.

---

## Bonus (sur demande)

- Intégration S3/GCS dans `hls_proxy`.
- Webhooks marchands.
- Support gating partiel via `/fragment`.

