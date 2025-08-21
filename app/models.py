from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import time, os


def _gen_bigint_id():
    """Generate a sortable 64-bit int: millis timestamp << 16 | 16 bits randomness."""
    return (int(time.time() * 1000) << 16) | int.from_bytes(os.urandom(2), 'big')

db = SQLAlchemy()

class Merchant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True)
    contact_url = db.Column(db.Text)
    webhook_url = db.Column(db.Text)
    status = db.Column(db.String(32), default='active')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url_or_blob_ref = db.Column(db.Text, nullable=False)
    mime_type = db.Column(db.String(128))
    type = db.Column(db.String(32), default='page')  # page|fragment|media
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchant.id'))
    name = db.Column(db.String(255), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'))
    default_duration_min = db.Column(db.Integer, nullable=False)
    policy_one_device = db.Column(db.Boolean, default=True)

class Code(db.Model):
    id = db.Column(db.BigInteger, primary_key=True, default=_gen_bigint_id)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchant.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    code_hash = db.Column(db.Text, nullable=False, unique=True)
    batch_id = db.Column(db.String(64))
    duration_min = db.Column(db.Integer)
    issued_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    expires_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(32), default='issued')

class Redemption(db.Model):
    id = db.Column(db.BigInteger, primary_key=True, default=_gen_bigint_id)
    code_id = db.Column(db.BigInteger, db.ForeignKey('code.id'))
    device_id = db.Column(db.String(64))
    first_redeemed_at = db.Column(db.DateTime(timezone=True))
    last_seen_at = db.Column(db.DateTime(timezone=True))
    access_jwt_id = db.Column(db.String(64))
    ip_first = db.Column(db.String(64))
    user_agent_first = db.Column(db.Text)

class AuditLog(db.Model):
    id = db.Column(db.BigInteger, primary_key=True, default=_gen_bigint_id)
    ts = db.Column(db.DateTime(timezone=True), server_default=func.now())
    actor_type = db.Column(db.String(32))
    actor_id = db.Column(db.String(64))
    event_type = db.Column(db.String(64))
    payload_json = db.Column(db.JSON)
