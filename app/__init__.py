from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from .config import Config
from .models import db
from flask_migrate import Migrate
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config())
    db.init_app(app)
    Migrate(app, db)
    # Trust reverse proxy headers (Render/Heroku)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    with app.app_context():
        db.create_all()

    from .routes_public import bp as public_bp
    from .routes_api import bp as api_bp
    from .routes_admin import bp as admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.get('/health')
    def health():
        return {'ok': True}

    return app
