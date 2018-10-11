import datetime

from nekoyume.block import Block
from nekoyume.move import Move
from nekoyume.node import Node


def test_block_validation(fx_user, fx_novice_status):
    move = fx_user.create_novice(fx_novice_status)
    block = Block.create(fx_user, [move])
    assert block.valid
    move.id = ('00000000000000000000000000000000'
               '00000000000000000000000000000000')
    assert not block.valid


def test_block_broadcast(fx_user, fx_session, fx_other_user, fx_other_session,
                         fx_server):
    assert fx_other_session.query(Block).count() == 0
    assert fx_session.query(Block).count() == 0

    fx_other_session.add(Node(url=fx_server.url,
                              last_connected_at=datetime.datetime.utcnow()))
    fx_other_session.commit()

    block = Block.create(fx_other_user, [])
    block.broadcast(session=fx_other_session)
    assert fx_other_session.query(Block).count() == 1
    assert fx_session.query(Block).count() == 1


def test_sync(fx_user, fx_session, fx_other_user, fx_other_session, fx_server,
              fx_novice_status):
    assert fx_other_session.query(Block).count() == 0
    assert fx_session.query(Block).count() == 0

    Block.sync(Node(url=fx_server.url), fx_other_session)
    assert fx_other_session.query(Block).count() == 0
    assert fx_session.query(Block).count() == 0

    Block.create(fx_other_user, [])
    Block.sync(Node(url=fx_server.url), fx_other_session)
    assert fx_other_session.query(Block).count() == 1
    assert fx_session.query(Block).count() == 0

    move = fx_user.create_novice(fx_novice_status)
    Block.create(fx_user, [move])
    Block.create(fx_user, [])
    Block.create(fx_user, [])

    assert fx_other_session.query(Block).count() == 1
    assert fx_other_session.query(Move).count() == 0
    assert fx_session.query(Block).count() == 3
    assert fx_session.query(Move).count() == 1

    Block.sync(Node(url=fx_server.url), fx_other_session)
    assert fx_other_session.query(Block).count() == 3
    assert fx_other_session.query(Move).count() == 1
    assert fx_session.query(Block).count() == 3
    assert fx_session.query(Move).count() == 1


def test_flush_session_while_syncing(fx_user, fx_session, fx_other_session,
                                     fx_novice_status):
    # 1. block validation failure scenario
    # syncing without flushing can cause block validation failure
    move = fx_user.create_novice(fx_novice_status)
    invalid_block = Block.create(fx_user, [move])
    fx_session.delete(invalid_block)

    # syncing valid blocks from another node
    new_blocks = [
        {
            "created_at": "2018-04-13 11:36:17.920869",
            "creator": "ET8ngv45qwhkDiJS1ZrUxndcGTzHxjPZDs",
            "difficulty": 0,
            "hash": "da0182c494660af0d9dd288839ceb86498708f38c800363cd46ed1730013a4d8", # noqa
            "id": 1,
            "version": 2,
            "moves": [],
            "prev_hash": None,
            "root_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", # noqa
            "suffix": "00"
        },
        {
            "created_at": "2018-04-13 11:36:17.935392",
            "creator": "ET8ngv45qwhkDiJS1ZrUxndcGTzHxjPZDs",
            "difficulty": 1,
            "hash": "014c44b9382a45c2a70d817c090e6b78af22b8f34b57fd7edb474344f25c439c", # noqa
            "id": 2,
            "version": 2,
            "moves": [],
            "prev_hash": "da0182c494660af0d9dd288839ceb86498708f38c800363cd46ed1730013a4d8", # noqa
            "root_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", # noqa
            "suffix": "0b"
        }
    ]

    def add_block(new_block):
        block = Block.deserialize(new_block)
        fx_session.add(block)
        return block

    valid_block1 = add_block(new_blocks[0])
    valid_block2 = add_block(new_blocks[1])

    assert invalid_block.hash == \
        fx_session.query(Block).get(valid_block2.id - 1).hash
    assert valid_block2.valid is False

    fx_session.query(Block).delete()

    # 2. valid scenario
    # flush session after deleting the invalid block
    move = fx_user.create_novice(fx_novice_status)
    invalid_block = Block.create(fx_user, [move])
    fx_session.delete(invalid_block)
    fx_session.flush()

    valid_block1 = add_block(new_blocks[0])
    valid_block2 = add_block(new_blocks[1])

    assert valid_block1.hash == \
        fx_session.query(Block).get(valid_block2.id - 1).hash
    assert valid_block2.valid
