import os
import urllib

from flask import Flask, redirect, url_for
from raven.contrib.flask import Sentry

from .api import api
from .game import babel, game
from .orm import db
from .tasks import celery
from .user import cache


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
    app.config['STATIC_URL'] = 'https://planetarium.is/nekoyume-unity/'
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

    @app.endpoint('static')
    def static(filename):
        static_url = app.config.get('STATIC_URL')

        if static_url:
            return redirect(urllib.parse.urljoin(static_url, filename))

        return app.send_static_file(filename)

    @app.template_global()
    def static_url(filename):
        static_url = app.config.get('STATIC_URL')

        if static_url:
            return urllib.parse.urljoin(static_url, filename)

        return url_for('static', filename=filename)
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
