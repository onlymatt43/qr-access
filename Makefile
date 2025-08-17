.PHONY: dev seed lint ci qr qr-install check-code check-jwt check-redis test

# --- Développement local ---
.PHONY: dev seed lint ci qr qr-install check-code check-jwt check-redis test db-init db-migrate db-upgrade

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