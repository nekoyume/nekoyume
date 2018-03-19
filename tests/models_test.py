from nekoyume.models import Block, Move


def test_move_confirmed():
    move = Move()
    assert not move.confirmed
    assert not move.valid
