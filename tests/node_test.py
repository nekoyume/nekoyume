from pytest_localserver.http import WSGIServer
from sqlalchemy.orm.session import Session

from nekoyume.node import Node


def test_node(fx_server: WSGIServer, fx_session: Session):
    assert fx_server.url
    assert Node.get(fx_server.url, session=fx_session)
    assert Node.get(fx_server.url, session=fx_session).url == fx_server.url
    assert Node.get(fx_server.url, session=fx_session).last_connected_at
