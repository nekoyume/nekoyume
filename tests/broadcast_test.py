import datetime
import typing
import unittest.mock

from flask import Flask
from pytest import fixture, mark
from pytest_localserver.http import WSGIServer
from requests.exceptions import ConnectionError, Timeout
from requests_mock import Mocker, mock
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.orm.session import Session
from typeguard import typechecked

from nekoyume.block import Block
from nekoyume.broadcast import (
    BlockBroadcaster,
    MoveBroadcaster,
    NodeBroadcaster,
)
from nekoyume.move import Move
from nekoyume.node import Node
from nekoyume.user import User


@fixture
def fx_other_server(request, fx_other_app: Flask) -> WSGIServer:
    server = WSGIServer(application=fx_other_app.wsgi_app)
    server.start()
    request.addfinalizer(server.stop)
    return server


@typechecked
def test_broadcast_node(
        fx_server: WSGIServer,
        fx_session: scoped_session,
        fx_other_server: WSGIServer,
        fx_other_session: Session,
):
    now = datetime.datetime.utcnow()
    node = Node(url=fx_server.url,
                last_connected_at=now)
    node2 = Node(url=fx_other_server.url,
                 last_connected_at=datetime.datetime.utcnow())
    fx_session.add(node)
    fx_session.commit()
    fx_other_session.add(node2)
    fx_other_session.commit()
    assert not fx_session.query(Node).filter(Node.url == node2.url).first()
    NodeBroadcaster.broadcast(serialized={'url': fx_other_server.url})
    assert fx_session.query(Node).filter(Node.url == node2.url).first()
    assert node.last_connected_at > now


@typechecked
def test_broadcast_node_same_url(fx_session: scoped_session):
    url = 'http://test.neko'
    now = datetime.datetime.utcnow()
    node = Node(url=url, last_connected_at=now)
    fx_session.add(node)
    fx_session.commit()
    with Mocker() as m:
        NodeBroadcaster.broadcast(serialized={'url': url}, sent_node=node)
        assert not m.called
    assert node.last_connected_at == now


@typechecked
def test_broadcast_my_node(fx_session: scoped_session):
    url = 'http://test.neko'
    now = datetime.datetime.utcnow()
    node = Node(url=url, last_connected_at=now)
    fx_session.add(node)
    fx_session.commit()
    with Mocker() as m:
        m.post('http://test.neko/nodes', json={'result': 'success'})
        NodeBroadcaster.broadcast({'url': url}, my_node=node)
        assert node.last_connected_at > now
        # check request.json value
        assert m.request_history[0].json() == {
            'url': 'http://test.neko',
            'sent_node': 'http://test.neko'
        }


@mark.parametrize('error', [ConnectionError, Timeout])
def broadcast_node_failed(fx_session: scoped_session,
                          fx_other_session: Session, error):
    now = datetime.datetime.utcnow()
    node = Node(url='http://test.neko',
                last_connected_at=now)
    node2 = Node(url='http://other.neko',
                 last_connected_at=datetime.datetime.utcnow())
    fx_session.add(node)
    fx_session.commit()
    fx_other_session.add(node2)
    fx_other_session.commit()
    assert not fx_session.query(Node).filter(Node.url == node2.url).first()
    with Mocker() as m:
        m.post('http://test.neko', exc=error)
        NodeBroadcaster.broadcast(serialized={'url': fx_other_server.url})
    assert not fx_session.query(Node).filter(Node.url == node2.url).first()
    assert node.last_connected_at == now


@typechecked
def test_broadcast_block(
        fx_server: WSGIServer,
        fx_session: scoped_session,
        fx_other_session: Session,
        fx_other_server: WSGIServer,
        fx_user: User
):
    now = datetime.datetime.utcnow()
    node = Node(url=fx_server.url,
                last_connected_at=now)
    node2 = Node(url=fx_other_server.url,
                 last_connected_at=datetime.datetime.utcnow())
    block = Block.create(fx_user, [])
    fx_session.add_all([node, node2, block])
    fx_session.flush()
    assert fx_session.query(Block).get(block.id)
    assert not fx_other_session.query(Block).get(block.id)
    BlockBroadcaster.broadcast(
        block.serialize(
            use_bencode=False,
            include_suffix=True,
            include_moves=True,
            include_hash=True
        )
    )
    assert node.last_connected_at > now
    assert fx_session.query(Block).count() == 1
    assert fx_other_session.query(Block).get(block.id)


@typechecked
def test_broadcast_block_my_node(fx_session: scoped_session, fx_user: User):
    block = Block.create(fx_user, [])
    url = 'http://test.neko'
    now = datetime.datetime.utcnow()
    node = Node(url=url, last_connected_at=now)
    fx_session.add(node)
    fx_session.flush()
    with Mocker() as m:
        m.post('http://test.neko/blocks', text='success')
        expected = serialized = block.serialize(
            use_bencode=False,
            include_suffix=True,
            include_moves=True,
            include_hash=True
        )
        BlockBroadcaster.broadcast(serialized, my_node=node)
        expected['sent_node'] = url
        assert node.last_connected_at > now
        assert node.last_connected_at > now
        # check request.json value
        assert m.request_history[0].json() == expected


@typechecked
def test_broadcast_block_same_node(fx_session: scoped_session, fx_user: User):
    block = Block.create(fx_user, [])
    url = 'http://test.neko'
    now = datetime.datetime.utcnow()
    node = Node(url=url, last_connected_at=now)
    fx_session.add(node)
    fx_session.flush()
    BlockBroadcaster.broadcast(
        block.serialize(
            use_bencode=False,
            include_suffix=True,
            include_moves=True,
            include_hash=True
        ),
        sent_node=node
    )
    assert node.last_connected_at == now


@mark.parametrize('error', [ConnectionError, Timeout])
def test_broadcast_block_raise_exception(
        fx_session: scoped_session, fx_user: User,
        error: typing.Union[ConnectionError, Timeout]
):
    block = Block.create(fx_user, [])
    url = 'http://test.neko'
    now = datetime.datetime.utcnow()
    node = Node(url=url, last_connected_at=now)
    fx_session.add(node)
    fx_session.flush()
    with Mocker() as m:
        m.post('http://test.neko/blocks', exc=error)
        BlockBroadcaster.broadcast(
            block.serialize(
                use_bencode=False,
                include_suffix=True,
                include_moves=True,
                include_hash=True
            )
        )
        assert node.last_connected_at == now


@mark.parametrize('limit, blocks, expected', [
    (1, 2, 3),
    (2, 5, 6),
])
def test_broadcast_block_retry(
        fx_session: scoped_session,
        fx_user: User, limit: int, blocks: int, expected: int
):
    for i in range(blocks):
        block = Block.create(fx_user, [])
    url = 'http://test.neko'
    now = datetime.datetime.utcnow()
    node = Node(url=url, last_connected_at=now)
    fx_session.add(node)
    fx_session.flush()
    patch = unittest.mock.patch('nekoyume.broadcast.BROADCAST_LIMIT', limit)
    with mock() as m, patch:
        m.register_uri('POST', 'http://test.neko/blocks', [
            {
                'json': {
                    'result': 'failed',
                    'block_id': 0,
                    'mesage': "new block isn't our next block."
                },
                'status_code': 403
            },
            {
                'json': {
                    'result': 'success',
                },
                'status_code': 200
            }
        ])
        BlockBroadcaster.broadcast(
            block.serialize(
                use_bencode=False,
                include_suffix=True,
                include_moves=True,
                include_hash=True
            )
        )
        assert m.call_count == expected
        assert node.last_connected_at > now


@typechecked
def test_broadcast_move(
        fx_server: WSGIServer,
        fx_session: scoped_session,
        fx_other_server: WSGIServer,
        fx_other_session: Session,
        fx_user: User,
        fx_novice_status: typing.Mapping[str, str],
):
    now = datetime.datetime.utcnow()
    node = Node(url=fx_server.url,
                last_connected_at=now)
    node2 = Node(url=fx_other_server.url,
                 last_connected_at=datetime.datetime.utcnow())
    move = fx_user.create_novice(fx_novice_status)
    fx_session.add_all([node, node2, move])
    fx_session.commit()
    assert not fx_other_session.query(Move).get(move.id)
    serialized = move.serialize(
        use_bencode=False,
        include_signature=True,
        include_id=True,
    )
    MoveBroadcaster.broadcast(serialized=serialized)
    assert fx_other_session.query(Move).get(move.id)
    assert node.last_connected_at > now


@typechecked
def test_broadcast_move_same_url(fx_session: scoped_session,
                                 fx_user: User,
                                 fx_novice_status: typing.Mapping[str, str]):
    url = 'http://test.neko'
    now = datetime.datetime.utcnow()
    node = Node(url=url, last_connected_at=now)
    move = fx_user.create_novice(fx_novice_status)
    fx_session.add_all([node, move])
    fx_session.commit()
    with Mocker() as m:
        serialized = move.serialize(
            use_bencode=False,
            include_signature=True,
            include_id=True,
        )
        MoveBroadcaster.broadcast(serialized=serialized, sent_node=node)
        assert not m.called
    assert node.last_connected_at == now


@typechecked
def test_broadcast_move_my_node(fx_session: scoped_session,
                                fx_user: User,
                                fx_novice_status: typing.Mapping[str, str]):
    url = 'http://test.neko'
    now = datetime.datetime.utcnow()
    node = Node(url=url, last_connected_at=now)
    move = fx_user.create_novice(fx_novice_status)
    fx_session.add_all([node, move])
    fx_session.commit()
    with Mocker() as m:
        m.post('http://test.neko/moves', json={'result': 'success'})
        expected = serialized = move.serialize(
            use_bencode=False,
            include_signature=True,
            include_id=True,
        )
        MoveBroadcaster.broadcast(serialized=serialized, my_node=node)
        expected['sent_node'] = 'http://test.neko'
        assert node.last_connected_at > now
        # check request.json value
        assert m.request_history[0].json() == expected


@mark.parametrize('error', [ConnectionError, Timeout])
def broadcast_move_failed(fx_session: scoped_session,
                          fx_user: User,
                          fx_novice_status: typing.Mapping[str, str],
                          error):
    now = datetime.datetime.utcnow()
    move = fx_user.create_novice(fx_novice_status)
    node = Node(url='http://test.neko',
                last_connected_at=now)
    fx_session.add_all([node, move])
    fx_session.commit()
    with Mocker() as m:
        serialized = move.serialize(
            use_bencode=False,
            include_signature=True,
            include_id=True,
        )
        m.post('http://test.neko', exc=error)
        MoveBroadcaster.broadcast(serialized=serialized)
    assert node.last_connected_at == now
