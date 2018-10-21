import typing
import unittest.mock

from coincurve import PrivateKey
from flask.testing import FlaskClient
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.orm.session import Session
from typeguard import typechecked

from nekoyume.block import Block
from nekoyume.game import get_unconfirmed_move
from nekoyume.move import Move
from nekoyume.node import Node
from nekoyume.user import User
from nekoyume.util import get_address


def test_login(fx_test_client):
    rv = fx_test_client.post('/login', data={
        'private_key': 'test'
    }, follow_redirects=False)

    assert rv.status == '302 FOUND'


def test_new_character_creation(fx_test_client, fx_session):
    privkey = PrivateKey()
    fx_test_client.post('/login', data={
        'private_key': privkey.to_hex(),
        'name': 'test_user',
    }, follow_redirects=True)

    assert fx_session.query(Move).filter_by(
        user_address=get_address(privkey.public_key),
        user_public_key=privkey.public_key.format(compressed=True),
        name='create_novice'
    ).first()


def test_move(fx_test_client, fx_session, fx_user, fx_private_key):
    rv = fx_test_client.post('/login', data={
        'private_key': fx_private_key.to_hex(),
        'name': 'test_user',
    }, follow_redirects=True)
    rv = fx_test_client.post('/new')
    Block.create(fx_user,
                 fx_session.query(Move).filter_by(block_id=None).all())

    rv = fx_test_client.post('/session_moves', data={
        'name': 'first_class',
        'class_': 'swordman',
    }, follow_redirects=True)
    Block.create(fx_user,
                 fx_session.query(Move).filter_by(block_id=None).all())

    avatar = fx_user.avatar()
    assert avatar.class_ == 'swordman'

    rv = fx_test_client.get('/')
    assert rv.status == '200 OK'

    rv = fx_test_client.post('/session_moves', data={
        'name': 'hack_and_slash'
    }, follow_redirects=True)
    assert rv.status == '200 OK'
    Block.create(fx_user,
                 fx_session.query(Move).filter_by(block_id=None).all())

    rv = fx_test_client.post('/session_moves', data={
        'name': 'sleep'
    }, follow_redirects=True)
    assert rv.status == '200 OK'
    Block.create(fx_user,
                 fx_session.query(Move).filter_by(block_id=None).all())

    rv = fx_test_client.post('/session_moves', data={
        'name': 'say',
        'content': 'hi!',
    }, follow_redirects=True)
    assert rv.status == '200 OK'
    Block.create(fx_user,
                 fx_session.query(Move).filter_by(block_id=None).all())


def test_logout(fx_test_client, fx_session, fx_user):
    rv = fx_test_client.post('/login', data={
        'private_key': 'test'
    }, follow_redirects=True)

    rv = fx_test_client.get('/logout')
    rv = fx_test_client.get('/')
    assert rv.status == '302 FOUND'


def test_get_unconfirmed_move(fx_session, fx_user, fx_novice_status):
    assert not get_unconfirmed_move(fx_user.address)
    move = fx_user.create_novice(fx_novice_status)
    assert get_unconfirmed_move(fx_user.address)
    # invalid move should not be recognized as unconfirmed move
    move.id = ('00000000000000000000000000000000'
               '00000000000000000000000000000000')
    assert not get_unconfirmed_move(fx_user.address)


def test_prevent_hack_and_slash_when_dead(
        fx_test_client: FlaskClient, fx_session: Session, fx_user: User,
        fx_private_key: PrivateKey, fx_novice_status: typing.Dict[str, str],
):
    fx_novice_status['hp'] = '1'
    move = fx_user.create_novice(fx_novice_status)
    Block.create(fx_user, [move])

    assert fx_user.avatar().dead is False
    while fx_user.avatar().hp > 0:
        move = fx_user.hack_and_slash()
        Block.create(fx_user, [move])
    assert fx_user.avatar().dead is True

    response = fx_test_client.post('/session_moves', data={
        'name': 'hack_and_slash'
    })
    assert response.status_code == 302


def test_export_private_key(
        fx_test_client: FlaskClient, fx_session: Session, fx_user: User,
        fx_private_key: PrivateKey
):
    fx_test_client.post('/login', data={
        'private_key': fx_private_key.to_hex(),
        'name': 'test_user',
    }, follow_redirects=True)
    response = fx_test_client.get('/export/')
    assert response.headers['Content-Disposition'] == \
        f'attachment;filename={fx_user.address}.csv'
    assert response.headers['Content-Type'] == 'text/csv'
    assert response.data == fx_private_key.to_hex().encode()


@typechecked
def test_get_new_novice_broadcasting(
        fx_test_client: FlaskClient, fx_user: User, fx_private_key: PrivateKey,
        fx_session: scoped_session,
):
    with unittest.mock.patch('nekoyume.game.multicast') as m:
        fx_test_client.post('/login', data={
            'private_key': fx_private_key.to_hex(),
            'name': 'test_user',
        }, follow_redirects=True)
        res = fx_test_client.get('/new')
        assert res.status_code == 200
        move = fx_session.query(Move).filter(
            Move.name == 'create_novice',
        ).first()
        assert move
        serialized = move.serialize(
            use_bencode=False,
            include_signature=True,
            include_id=True,
        )
        assert m.called
        args = m.call_args[1]
        assert serialized == args['serialized']
        my_node = args['my_node']
        assert isinstance(my_node, Node)
        assert my_node.url == 'http://localhost'
        broadcast = args['broadcast']
        assert isinstance(broadcast, typing.Callable)
        assert broadcast.__name__ == 'broadcast_move'


@typechecked
def test_post_move_broadcasting(
        fx_test_client: FlaskClient, fx_user: User, fx_private_key: PrivateKey,
        fx_session: scoped_session,
):
    with unittest.mock.patch('nekoyume.game.multicast') as m:
        fx_test_client.post('/login', data={
            'private_key': fx_private_key.to_hex(),
            'name': 'test_user',
        }, follow_redirects=True)
        fx_test_client.post('/new')
        Block.create(fx_user,
                     fx_session.query(Move).filter_by(block_id=None).all())
        assert not get_unconfirmed_move(fx_user.address)
        res = fx_test_client.post('/session_moves', data={
            'name': 'hack_and_slash'
        })
        assert res.status_code == 302
        move = fx_session.query(Move).filter(
            Move.name == 'hack_and_slash',
        ).first()
        assert move
        serialized = move.serialize(
            use_bencode=False,
            include_signature=True,
            include_id=True,
        )
        assert m.called
        args = m.call_args[1]
        assert serialized == args['serialized']
        my_node = args['my_node']
        assert isinstance(my_node, Node)
        assert my_node.url == 'http://localhost'
        broadcast = args['broadcast']
        assert isinstance(broadcast, typing.Callable)
        assert broadcast.__name__ == 'broadcast_move'
