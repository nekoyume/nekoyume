import datetime

from flask import Flask
from pytest import fixture
from pytest_localserver.http import WSGIServer
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.orm.session import Session
from typeguard import typechecked

from nekoyume.node import Node


@typechecked
def test_node(fx_server: WSGIServer, fx_session: scoped_session):
    assert fx_server.url
    assert Node.get(fx_server.url, session=fx_session)
    assert Node.get(fx_server.url, session=fx_session).url == fx_server.url
    assert Node.get(fx_server.url, session=fx_session).last_connected_at


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
    node = Node(url=fx_server.url,
                last_connected_at=datetime.datetime.utcnow())
    node2 = Node(url=fx_other_server.url,
                 last_connected_at=datetime.datetime.utcnow())
    fx_session.add(node)
    fx_session.commit()
    fx_other_session.add(node2)
    fx_other_session.commit()
    assert not fx_session.query(Node).filter(Node.url == node2.url).first()
    Node.broadcast(
        endpoint=Node.post_node_endpoint,
        serialized_obj={'url': fx_other_server.url},
        session=fx_session
    )
    assert fx_session.query(Node).filter(Node.url == node2.url).first()
