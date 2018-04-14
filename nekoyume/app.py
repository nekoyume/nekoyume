import os

from flask import Flask

from nekoyume.models import cache, db
from nekoyume.api import api
from nekoyume.game import babel, game
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
    app.secret_key = b'\xc2o\x81?u+\x14j%\x99\xc5\xa6\x83\x06`\xfch$\n"a0\x96\x8c' # noqa
    app.register_blueprint(api)
    app.register_blueprint(game)

    db.app = app
    db.init_app(app)

    babel.app = app
    babel.init_app(app)

    app.config.update(
        CELERY_BROKER_URL=os.environ.get(
            'REDIS_URL', 'redis://localhost:6379'),
        CELERY_RESULT_BACKEND=os.environ.get(
            'REDIS_URL', 'redis://localhost:6379'))
    return app


app = create_app()
cel = make_celery(app)
cache.init_app(app, config={'CACHE_TYPE': 'redis',
                            'CACHE_REDIS_URL': os.environ.get(
                                'REDIS_URL', 'redis://localhost:6379'
                            )})


def run():
    from gunicorn.app import wsgiapp
    wsgiapp.run()
