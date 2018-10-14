from pytest_localserver.http import WSGIServer
from sqlalchemy.orm.scoping import scoped_session
from typeguard import typechecked

from nekoyume.node import Node


@typechecked
def test_node(fx_server: WSGIServer, fx_session: scoped_session):
    assert fx_server.url
    assert Node.get(fx_server.url, session=fx_session)
    assert Node.get(fx_server.url, session=fx_session).url == fx_server.url
    assert Node.get(fx_server.url, session=fx_session).last_connected_at
