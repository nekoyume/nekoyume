import pytest

from nekoyume.models import Node


def test_post_node(fx_other_test_client, fx_server, fx_other_session):
    rv = fx_other_test_client.post('/nodes', data={
        'url': fx_server.url
    }, follow_redirects=True)

    assert rv.status == '200 OK'

    assert fx_other_session.query(Node).filter_by(
        url=fx_server.url
    ).first()


def test_get_blocks(fx_test_client, fx_user):
    block = fx_user.create_block([])

    rv = fx_test_client.get(f'/blocks')
    assert rv.status == '200 OK'
    assert block.hash.encode() in rv.data

    rv = fx_test_client.get(f'/blocks/{block.id}')
    assert rv.status == '200 OK'
    assert block.hash.encode() in rv.data

    rv = fx_test_client.get(f'/blocks/{block.hash}')
    assert rv.status == '200 OK'
    assert block.hash.encode() in rv.data
