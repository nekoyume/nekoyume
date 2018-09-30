import datetime
import hashlib
import typing

from sqlalchemy.exc import IntegrityError
from typeguard import typechecked

from . import hashcash
from .exc import (
    InvalidBlockError,
    InvalidMoveError,
)
from .models import (
    MAX_BLOCK_INTERVAL,
    MIN_BLOCK_INTERVAL,
    PROTOCOL_VERSION,
    Block,
    Move,
    User,
)


@typechecked
def create_block(
        user: User,
        moves: typing.List[Move],
        commit: bool=True,
        echo: typing.Optional[typing.Callable]=None,
        sleep: typing.Union[int, float]=0.0,
) -> Block:
    """ Create a block. """
    for move in moves:
        if not move.valid:
            raise InvalidMoveError(move)
    block = Block(version=PROTOCOL_VERSION)
    block.root_hash = hashlib.sha256(
        ''.join(sorted((m.id for m in moves))).encode('utf-8')
    ).hexdigest()
    block.creator = user.address
    block.created_at = datetime.datetime.utcnow()

    prev_block = user.session.query(Block).order_by(
        Block.id.desc()
    ).first()
    if prev_block:
        block.id = prev_block.id + 1
        block.prev_hash = prev_block.hash
        block.difficulty = prev_block.difficulty
        difficulty_check_block = user.session.query(Block).get(
            max(1, block.id - 10)
        )
        avg_timedelta = (
            (block.created_at - difficulty_check_block.created_at) /
            (block.id - difficulty_check_block.id)
        )
        if echo:
            echo(
                f'avg: {avg_timedelta}, difficulty: {block.difficulty}'
            )
        if avg_timedelta <= MIN_BLOCK_INTERVAL:
            block.difficulty = max(0, block.difficulty + 1)
        elif avg_timedelta > MAX_BLOCK_INTERVAL:
            block.difficulty = max(0, block.difficulty - 1)
    else:
        #: Genesis block
        block.id = 1
        block.prev_hash = None
        block.difficulty = 0
        sleep = 0

    block.suffix = hashcash._mint(block.serialize(), bits=block.difficulty,
                                  sleep=sleep)
    if user.session.query(Block).get(block.id):
        return None
    block.hash = hashlib.sha256(
        block.serialize() + block.suffix
    ).hexdigest()

    for move in moves:
        move.block = block

    if not block.valid:
        raise InvalidBlockError

    if commit:
        try:
            user.session.add(block)
            user.session.commit()
        except IntegrityError:
            return None

    return block
