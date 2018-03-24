import pytest

from nekoyume.models import Node


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
