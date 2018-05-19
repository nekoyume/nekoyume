from functools import wraps

from flask import (Blueprint, g, request, redirect, render_template,
                   session, url_for)
from flask_babel import Babel
from sqlalchemy import func

from nekoyume.models import cache, db, LevelUp, Move, Node, User


game = Blueprint('game', __name__, template_folder='templates')
babel = Babel()


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(['ko', 'en'])


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('private_key') is None:
            return redirect(url_for('.get_login', next=request.url))
        else:
            g.user = User(session['private_key'])
        return f(*args, **kwargs)
    return decorated_function


@game.route('/login', methods=['GET'])
def get_login():
    return render_template('login.html')


@game.route('/login', methods=['POST'])
def post_login():
    session['private_key'] = request.values.get('private_key')
    if 'next' in request.values:
        return redirect(request.values.get('next'))
    else:
        return redirect(url_for('.get_dashboard'))


@game.route('/logout', methods=['GET'])
@login_required
def get_logout():
    del session['private_key']
    return redirect(url_for('game.get_login'))


@cache.memoize(60)
def get_rank():
    return db.session.query(
        LevelUp.user, func.count(LevelUp.id)
    ).group_by(LevelUp.user).order_by(
        func.count(LevelUp.id).desc()
    ).limit(10).all()


@game.route('/')
@login_required
def get_dashboard():
    if not g.user.avatar():
        return redirect(url_for('.get_new_novice'))

    unconfirmed_move = Move.query.filter_by(
        user=g.user.address, block=None
    ).first()

    feed = g.user.moves
    # for caching
    for move in reversed(feed.limit(10).all()):
        avatar, result = move.execute()
    return render_template('dashboard.html',
                           unconfirmed_move=unconfirmed_move,
                           feed=feed.order_by(Move.block_id.desc()),
                           rank=get_rank())


@game.route('/new')
@login_required
def get_new_novice():
    if not g.user.avatar():
        move = Move.query.filter_by(
            user=g.user.address,
            name='create_novice',
        ).first()
        if not move:
            move = g.user.create_novice({
                'strength': '12',
                'dexterity': '12',
                'constitution': '9',
                'intelligence': '10',
                'wisdom': '8',
                'charisma': '13'})
            db.session.add(move)
            db.session.commit()
            move.broadcast(
                my_node=Node(url=f'{request.scheme}://{request.host}')
            )
        return render_template('new.html', move=move)
    return redirect(url_for('.get_dashboard'))


@game.route('/session_moves', methods=['POST'])
@login_required
def post_move():
    unconfirmed_move = Move.query.filter_by(
        user=g.user.address, block=None
    ).first()

    if unconfirmed_move:
        return redirect(url_for('.get_dashboard'))

    if request.values.get('name') == 'hack_and_slash':
        move = g.user.hack_and_slash(request.values.get('weapon'),
                                     request.values.get('armor'),
                                     request.values.get('food'),)
    if request.values.get('name') == 'sleep':
        move = g.user.sleep()
    if request.values.get('name') == 'level_up':
        move = g.user.level_up(request.values.get('new_status'))
    if request.values.get('name') == 'say':
        move = g.user.say(request.values.get('content'))
    if request.values.get('name') == 'send':
        move = g.user.send(request.values.get('item'),
                           request.values.get('amount'),
                           request.values.get('receiver'))
    if request.values.get('name') == 'combine':
        move = g.user.combine(request.values.get('item1'),
                              request.values.get('item2'),
                              request.values.get('item3'))

    if move:
        move.broadcast(my_node=Node(url=f'{request.scheme}://{request.host}'))
    return redirect(url_for('.get_dashboard'))
