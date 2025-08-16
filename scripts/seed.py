import os, time, sys, pathlib
# Ensure project root is on PYTHONPATH when running directly
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
