dev:
	flask --app app:create_app run --reload

seed:
	python scripts/seed.py

lint:
	flake8 app

ci: lint
	pytest

# Utilise QR_URL si fournie: make qr QR_URL="https://.../redeem?c=XXXX"
.PHONY: qr qr-install

qr-install:
	python3 -m pip install --upgrade pip
	python3 -m pip install "qrcode[pil]"

qr:
	python3 scripts/make_qr.py "$(QR_URL)"
