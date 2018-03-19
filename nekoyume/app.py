from functools import wraps
import os

from flask import (Flask, g, request, redirect, render_template, session,
                   url_for)

from nekoyume.models import cache, db, Node, Move, User
from nekoyume.api import api
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


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('private_key') is None:
            return redirect(url_for('get_login', next=request.url))
        else:
            g.user = User(session['private_key'])
        return f(*args, **kwargs)
    return decorated_function


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///yume.db')
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.secret_key = b'\xc2o\x81?u+\x14j%\x99\xc5\xa6\x83\x06`\xfch$\n"a0\x96\x8c' # noqa
    app.register_blueprint(api)
    db.init_app(app)
    app.config.update(
        CELERY_BROKER_URL=os.environ.get(
            'REDIS_URL', 'redis://localhost:6379'),
        CELERY_RESULT_BACKEND=os.environ.get(
            'REDIS_URL', 'redis://localhost:6379'))
    return app


app = create_app()
cel = make_celery(app)
cache.init_app(app, config={'CACHE_TYPE': 'simple'})


@app.route('/login', methods=['GET'])
def get_login():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def post_login():
    session['private_key'] = request.values.get('private_key')
    if 'next' in request.values:
        return redirect(request.values.get('next'))
    else:
        return redirect(url_for('get_dashboard'))


@app.route('/')
@login_required
def get_dashboard():
    unconfirmed_move = Move.query.filter_by(
        user=g.user.address, block=None
    ).first()
    return render_template('dashboard.html',
                           unconfirmed_move=unconfirmed_move)


@app.route('/new')
@login_required
def get_new_novice():
    if not g.user.avatar():
        move = g.user.create_novice({
            'strength': '15',
            'dexterity': '12',
            'constitution': '16',
            'intelligence': '9',
            'wisdom': '8',
            'charisma': '13'})
        db.session.add(move)
        db.session.commit()
    return move.id


@app.route('/session_moves', methods=['POST'])
@login_required
def post_move():
    if request.values.get('name') in ('hack_and_slash', 'sleep'):
        move = getattr(g.user, request.values.get('name'))()
    if request.values.get('name') == 'level_up':
        move = g.user.level_up(request.values.get('new_status'))
    if request.values.get('name') == 'say':
        move = g.user.say(request.values.get('content'))
    if request.values.get('name') == 'send':
        move = g.user.send(request.values.get('item'),
                           request.values.get('amount'),
                           request.values.get('receiver'))

    move.broadcast(my_node=Node(url=f'{request.scheme}://{request.host}'))
    return redirect(url_for('get_dashboard'))


def run():
    from gunicorn.app import wsgiapp
    wsgiapp.run()
