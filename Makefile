dev:
	flask --app app:create_app run --reload

seed:
	python scripts/seed.py

lint:
	flake8 app

ci: lint
	pytest
