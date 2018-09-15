import os

from flask import Flask
from raven.contrib.flask import Sentry

from nekoyume.api import api
from nekoyume.game import babel, game
from nekoyume.models import cache, db
from nekoyume.tasks import celery


def make_celery(app):
    celery.name = app.import_name
    celery.conf.update(
        result_backend=app.config['CELERY_RESULT_BACKEND'],
        broker_url=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///yume.db')
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    try:
        with open('.secret_key', 'rb') as f:
            app.secret_key = f.read()
    except FileNotFoundError:
        app.secret_key = os.urandom(64)
        f = open('.secret_key', 'wb')
        f.write(app.secret_key)
        f.close()

    app.register_blueprint(api)
    app.register_blueprint(game)

    db.app = app
    db.init_app(app)

    babel.app = app
    babel.init_app(app)

    app.config.update(
        CELERY_BROKER_URL=os.environ.get(
            'CELERY_BROKER_URL', 'sqla+sqlite:///yume_broker.db'),
        CELERY_RESULT_BACKEND=os.environ.get(
            'CELERY_RESULT_BACKEND', 'db+sqlite:///yume_reuslt.db'))
    return app


app = create_app()
cel = make_celery(app)

cache_type = os.environ.get('CACHE_TYPE', 'filesystem')
if cache_type == 'redis':
    cache_config = {
        'CACHE_TYPE': cache_type,
        'CACHE_REDIS_URL': os.environ.get(
            'REDIS_URL', 'redis://localhost:6379'
        ),
    }
else:
    cache_config = {
        'CACHE_TYPE': cache_type,
        'CACHE_DIR': os.environ.get('CACHE_DIR', '.yumecache'),
    }

cache.init_app(app, cache_config)
sentry = Sentry(app)


def run():
    from gunicorn.app import wsgiapp
    wsgiapp.run()
