# QR Access Flask MVP

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app:create_app
flask run
```

## Notes
- Le flux `/redeem` retourne un JWT d’accès et un `content_id`.
- L’endpoint `/content/<id>` est un stub : ajoutez la validation complète du JWT (clé publique) et remplacez par le proxy réel (fragments/médias/HLS).
- Ajoutez Alembic pour les migrations et l’intégration Render (Postgres/Redis) selon votre environnement.
