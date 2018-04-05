"""
    Imports
"""
import sys

from flask import Flask
from flask_mongoengine import MongoEngine

from celery import Celery

from mongoengine import connect, MongoEngineConnectionError
from .config import DB_HOST, DB_PORT, DB_NAME
from .config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

DB = MongoEngine()

def make_celery(app):
    """
    Create celery instance.
    """
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    class ContextTask(celery.Task): # pylint: disable-all
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return celery.Task.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

def create_app(**config_overrides):
    """
    Creates a flask application with the desired configuration settings
    and connects it to the database.
    """
    app = Flask(__name__)

    # Initialize configuration
    app.config.from_object('teamserver.config')
    app.config['MONGODB_SETTINGS'] = {
        'db': DB_NAME,
        'host': DB_HOST,
        'port': DB_PORT
    }
    app.config['CELERY_BROKER_URL'] = CELERY_BROKER_URL
    app.config['CELERY_RESULT_BACKEND'] = CELERY_RESULT_BACKEND

    # Override configuration options
    app.config.update(config_overrides)

    # Initialize the database
    try:
        DB.init_app(app)
    except MongoEngineConnectionError as conn_err:
        from .models import log
        log('FATAL', 'Failed to connect to database.')
        log('DEBUG', conn_err)
        print(conn_err)
        sys.exit('Could not connect to database.')

    # Initialize Celery
    from teamserver.event import CELERY
    CELERY = make_celery(app)

    # Import endpoints
    from teamserver.router import API
    app.register_blueprint(API)


    return app
