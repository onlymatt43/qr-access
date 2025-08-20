issue-qr:
	@echo "Issuing QR via admin API…"
	@python3 scripts/issue_qr.py

issue-qr-png:
	@echo "Issuing QR and downloading PNG…"
	@WANT_PNG=1 python3 scripts/issue_qr.py

test-webhook:
	@echo "Sending sample payment webhook…"
	@python3 - <<'PY'
	import os, json, requests
	BASE=os.environ.get('BASE_URL','http://localhost:5000')
	KEY=os.environ.get('WEBHOOK_KEY','dev')
	body={
	  'event':'payment.succeeded',
	  'data':{'merchant_id':1,'product_id':1,'duration_min':15}
	}
	r=requests.post(f"{BASE}/admin/payment-webhook", headers={'X-Webhook-Key':KEY,'Content-Type':'application/json'}, data=json.dumps(body))
	print(r.status_code, r.text)
	PY
.PHONY: dev seed lint ci qr qr-install check-code check-jwt check-redis test db-init db-migrate db-upgrade

# --- Développement local ---
dev:
	flask --app app:create_app run --reload

seed:
	python scripts/seed.py

lint:
	flake8 app

ci: lint
	pytest

# --- QR Codes ---
qr-install:
	python3 -m pip install --upgrade pip
	python3 -m pip install "qrcode[pil]"

qr:
	@if [ -z "$(QR_URL)" ]; then \
		echo "Error: QR_URL is not set. Usage: make qr QR_URL=\"https://.../redeem?c=XXXX\""; \
		exit 1; \
	fi; \
	python3 scripts/make_qr.py "$(QR_URL)"

# --- Vérifications ---
check-code:
	python3 scripts/check_codes.py "$(OPAQUE)" "$(MERCHANT_SALT)"

check-jwt:
	python3 scripts/check_jwt.py "$(JWT)" "-"

check-redis:
	python3 scripts/check_redis.py "$(REDIS_URL)" "$(CODE_ID)" "$(JTI)"

# --- Tests unitaires ---
test:
	pytest -q --disable-warnings

# Database migrations (Flask-Migrate)
db-init:
	flask --app app:create_app db init

db-migrate:
	flask --app app:create_app db migrate -m "auto"

db-upgrade:
	flask --app app:create_app db upgrade
