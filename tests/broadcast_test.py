import datetime

from flask import Flask
from pytest import fixture, mark
from pytest_localserver.http import WSGIServer
from requests.exceptions import ConnectionError, Timeout
from requests_mock import Mocker
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.orm.session import Session
from typeguard import typechecked

from nekoyume.broadcast import broadcast_node
from nekoyume.node import Node


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
    broadcast_node(serialized={'url': fx_other_server.url})
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
        broadcast_node(serialized={'url': url}, sent_node=node)
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
        broadcast_node({'url': url}, my_node=node)
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
        broadcast_node(serialized={'url': fx_other_server.url})
    assert not fx_session.query(Node).filter(Node.url == node2.url).first()
    assert node.last_connected_at == now
