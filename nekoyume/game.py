import datetime
from functools import wraps

from flask import (Blueprint, Flask, g, request, redirect, render_template,
                   session, url_for)

from nekoyume.tasks import block_broadcast, move_broadcast
from nekoyume.models import db, Block, Node, Move, User


game = Blueprint('game', __name__, template_folder='templates')


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


@game.route('/')
@login_required
def get_dashboard():
    if not g.user.avatar():
        return redirect(url_for('.get_new_novice'))
    unconfirmed_move = Move.query.filter_by(
        user=g.user.address, block=None
    ).first()
    return render_template('dashboard.html',
                           unconfirmed_move=unconfirmed_move)


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
                'strength': '15',
                'dexterity': '12',
                'constitution': '16',
                'intelligence': '9',
                'wisdom': '8',
                'charisma': '13'})
            db.session.add(move)
            db.session.commit()
        return move.id
    return redirect(url_for('.get_dashboard'))


@game.route('/session_moves', methods=['POST'])
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

    if move:
        move.broadcast(my_node=Node(url=f'{request.scheme}://{request.host}'))
    return redirect(url_for('.get_dashboard'))
