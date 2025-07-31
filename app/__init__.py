
from flask import Flask
from flask_cors import CORS
from app.routes.sap import sap_bp
from app.routes.inspections import inspections_bp

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_pyfile('../config.py')

    app.register_blueprint(sap_bp, url_prefix='/api')
    app.register_blueprint(inspections_bp, url_prefix='/api')

    return app
