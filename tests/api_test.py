import pytest

from nekoyume.models import Node


def test_get_blocks(fx_test_client, fx_user):
    move = fx_user.sleep()

    rv = fx_test_client.get(f'/moves/{move.id}')
    assert rv.status == '200 OK'
    assert move.id.encode() in rv.data

    block = fx_user.create_block([move])

    rv = fx_test_client.get(f'/blocks')
    assert rv.status == '200 OK'
    assert block.hash.encode() in rv.data
    assert move.id.encode() in rv.data

    rv = fx_test_client.get(f'/blocks/{block.id}')
    assert rv.status == '200 OK'
    assert block.hash.encode() in rv.data
    assert move.id.encode() in rv.data

    rv = fx_test_client.get(f'/blocks/{block.hash}')
    assert rv.status == '200 OK'
    assert block.hash.encode() in rv.data
