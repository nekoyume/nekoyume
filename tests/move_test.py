import datetime

from coincurve import PrivateKey
from pytest import fixture, raises

from nekoyume.block import Block
from nekoyume.exc import InvalidMoveError
from nekoyume.move import (
    CreateNovice,
    HackAndSlash,
    LevelUp,
    Move,
    Say,
    Sleep,
)
from nekoyume.node import Node
from nekoyume.user import User


@fixture
def fx_user2(fx_session):
    user = User(PrivateKey())
    user.session = fx_session
    return user


def test_move_confirmed_and_validation(fx_user, fx_novice_status):
    move = Move()
    assert not move.confirmed
    assert not move.valid

    move = fx_user.create_novice(fx_novice_status)

    assert not move.confirmed
    assert move.valid

    block = Block.create(fx_user, [move])

    assert move.block_id
    assert move.confirmed
    assert move.valid

    move.tax = 1
    assert not move.valid
    assert not block.valid


def test_level_up(fx_user, fx_novice_status):
    move = fx_user.create_novice(fx_novice_status)
    Block.create(fx_user, [move])

    while True:
        if fx_user.avatar().exp >= 8:
            break
        move = fx_user.hack_and_slash()
        Block.create(fx_user, [move])

        if fx_user.avatar().hp <= 0:
            move = fx_user.sleep()
            Block.create(fx_user, [move])

    assert fx_user.avatar().level >= 2


def test_avatar_basic_moves(fx_user, fx_novice_status):
    moves = [
        CreateNovice(details=fx_novice_status),
        HackAndSlash(),
        Sleep(),
        Say(details={'content': 'hi'}),
        LevelUp(details={'new_status': 'strength'}),
    ]
    for move in moves:
        move = fx_user.move(move)
        block = Block.create(fx_user, [move])
        assert move.valid
        assert move.confirmed
        assert block.valid
        assert fx_user.avatar(block.id)


def test_move_broadcast(fx_user, fx_session, fx_other_user, fx_other_session,
                        fx_server, fx_novice_status):
    assert fx_other_session.query(Move).count() == 0
    assert fx_session.query(Move).count() == 0

    fx_other_session.add(Node(url=fx_server.url,
                              last_connected_at=datetime.datetime.utcnow()))
    fx_other_session.commit()

    move = fx_other_user.create_novice(fx_novice_status)
    assert not fx_session.query(Move).get(move.id)

    move.broadcast(session=fx_other_session)
    assert fx_session.query(Move).get(move.id)


def test_hack_and_slash_execute(fx_user, fx_novice_status):
    move = fx_user.create_novice(fx_novice_status)
    Block.create(fx_user, [move])
    avatar = fx_user.avatar()
    avatar.hp = 0
    move = fx_user.move(HackAndSlash())
    Block.create(fx_user, [move])
    with raises(InvalidMoveError):
        move.execute(avatar)
