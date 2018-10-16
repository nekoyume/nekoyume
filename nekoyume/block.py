import datetime
import hashlib
from typing import Callable, Optional, Type, Union

from bencode import bencode
from requests import get
from requests.exceptions import ConnectionError, Timeout
from sqlalchemy.exc import IntegrityError
from typeguard import typechecked

from . import hashcash
from .exc import (
    InvalidBlockError,
    InvalidMoveError,
    NodeUnavailable,
)
from .node import Node
from .orm import db
from .user import User


MIN_BLOCK_INTERVAL = datetime.timedelta(0, 5)
MAX_BLOCK_INTERVAL = datetime.timedelta(0, 15)
PROTOCOL_VERSION: int = 2


class Block(db.Model):
    """This object contains block information."""

    __tablename__ = 'block'
    #: block id
    id = db.Column(db.Integer, primary_key=True)
    #: protocol version
    version = db.Column(db.Integer, default=PROTOCOL_VERSION, nullable=False)
    #: current block's hash
    hash = db.Column(db.String, nullable=False, index=True, unique=True)
    #: previous block's hash
    prev_hash = db.Column(db.String, index=True)
    #: block creator's address
    creator = db.Column(db.String, nullable=False, index=True)
    #: hash of every linked move's ordered hash list
    root_hash = db.Column(db.String, nullable=False)
    #: suffix for hashcash
    suffix = db.Column(db.LargeBinary, nullable=False)
    #: difficulty of hashcash
    difficulty = db.Column(db.Integer, nullable=False)
    #: block creation datetime
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.utcnow)
    size_limit = 10000
    __table_args__ = (
        db.CheckConstraint(id > 0),
        db.CheckConstraint(
            db.case([
                (id == 1, prev_hash.is_(None)),
            ], else_=prev_hash.isnot(None))
        ),
        db.CheckConstraint((id == 1) | (difficulty > 0)),
    )

    @classmethod
    def deserialize(cls, serialized: dict) -> 'Block':
        return cls(
            id=serialized['id'],
            version=serialized['version'],
            creator=serialized['creator'],
            created_at=datetime.datetime.strptime(
                serialized['created_at'],
                '%Y-%m-%d %H:%M:%S.%f'
            ),
            prev_hash=serialized['prev_hash'],
            hash=serialized['hash'],
            difficulty=serialized['difficulty'],
            suffix=bytes.fromhex(serialized['suffix']),
            root_hash=serialized['root_hash'],
        )

    @property
    def valid(self) -> bool:
        """Check if this object is valid or not"""
        stamp = self.serialize() + self.suffix
        valid = (self.hash == hashlib.sha256(stamp).hexdigest())
        valid = valid and hashcash.check(stamp, self.suffix, self.difficulty)

        valid = valid and (
            len(self.serialize(True, True, True, True)) <= Block.size_limit
        )

        if self.id > 1:
            prev_block = Block.query.get(self.id - 1)
            if not prev_block:
                return False
            valid = valid and self.prev_hash == prev_block.hash

            difficulty = prev_block.difficulty
            difficulty_check_block = Block.query.get(
                max(1, self.id - 10)
            )
            avg_timedelta = (
                (self.created_at - difficulty_check_block.created_at) /
                (self.id - difficulty_check_block.id)
            )
            if avg_timedelta <= MIN_BLOCK_INTERVAL:
                valid = valid and self.difficulty == max(1, difficulty + 1)
            elif avg_timedelta > MAX_BLOCK_INTERVAL:
                valid = valid and self.difficulty == max(1, difficulty - 1)
            else:
                valid = valid and self.difficulty == difficulty
        else:
            valid = valid and self.prev_hash is None
            valid = valid and self.difficulty == 0

        valid = valid and self.root_hash == hashlib.sha256(
            ''.join(sorted((m.id for m in self.moves))).encode('utf-8')
        ).hexdigest()

        for move in self.moves:
            valid = valid and move.valid
        return valid

    def serialize(self,
                  use_bencode: bool=True,
                  include_suffix: bool=False,
                  include_moves: bool=False,
                  include_hash: bool=False):
        """
        This function serialize block.

        :param    use_bencode: check if you want to encode using bencode.
        :param include_suffix: check if you want to include suffix.
        :param  include_moves: check if you want to include linked moves.
        :param   include_hash: check if you want to include block hash.
        """
        binary = (lambda x: x) if use_bencode else bytes.hex
        serialized = dict(
            id=self.id,
            creator=self.creator,
            prev_hash=self.prev_hash,
            difficulty=self.difficulty,
            root_hash=self.root_hash,
            created_at=str(self.created_at),
            version=self.version,
        )
        if include_suffix:
            serialized['suffix'] = binary(self.suffix)

        if include_moves:
            serialized['moves'] = [m.serialize(
                use_bencode=False,
                include_signature=True,
                include_id=True,
            ) for m in self.moves]

        if include_hash:
            serialized['hash'] = self.hash

        if use_bencode:
            if self.prev_hash is None:
                del serialized['prev_hash']
            serialized = bencode(serialized)
        return serialized

    @classmethod
    def sync(cls, node: Node=None, session=db.session, echo=None) -> bool:
        """
        Sync blockchain with other node.

        :param node: sync target :class:`nekoyume.node.Node`.
        """
        from .move import Move
        if not node:
            nodes = Node.query.order_by(
                Node.last_connected_at.desc()
            ).limit(10)
        else:
            nodes = [node]

        if not nodes:
            return False

        node_last_block = None
        for n in nodes:
            try:
                response = get(
                    f"{n.url}{Node.get_blocks_endpoint}/last",
                    timeout=3
                )
                if response.status_code != 200:
                    continue
                if (not node_last_block or
                   node_last_block['id'] < response.json()['block']['id']):
                    node_last_block = response.json()['block']
                    node = n
            except (ConnectionError, KeyError, Timeout):
                continue

        last_block = session.query(Block).order_by(Block.id.desc()).first()

        if not node_last_block:
            return True

        #: If my chain is the longest one, we don't need to do anything.
        if last_block and last_block.id >= node_last_block['id']:
            return True

        if last_block:
            # TODO: Very hard to understand. fix this easily.
            try:
                branch_point = find_branch_point(node, session, last_block.id,
                                                 last_block.id)
                if branch_point == last_block.id:
                    branch_point = last_block.id
                else:
                    branch_point = find_branch_point(node, session, 0,
                                                     last_block.id)
            except NodeUnavailable:
                return
        else:
            branch_point = 0

        for block in session.query(Block).filter(Block.id > branch_point):
            for move in block.moves:
                move.block_id = None
            session.delete(block)

        # Flush the above deletions to the database.
        # If we don't flush here,
        # stale objects can be fetched when validating blocks.
        session.flush()

        from_ = branch_point + 1
        limit = 1000
        while True:
            if echo:
                echo(f'Syncing blocks...(from: {from_})')
            response = get(f"{node.url}{Node.get_blocks_endpoint}",
                           params={'from': from_,
                                   'to': from_ + limit - 1})
            if response.status_code != 200:
                break
            if len(response.json()['blocks']) == 0:
                break
            for new_block in response.json()['blocks']:
                block = Block.deserialize(new_block)

                for new_move in new_block['moves']:
                    move = session.query(Move).get(new_move['id'])
                    if not move:
                        move = Move.deserialize(new_move, block.id)
                    if not move.valid:
                        session.rollback()
                        raise InvalidMoveError
                    block.moves.append(move)
                    session.add(move)

                if not block.valid:
                    session.rollback()
                    raise InvalidBlockError
                session.add(block)
            if len(response.json()['blocks']) < 1000:
                break
            from_ += limit
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return False

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return False
        return True

    @classmethod
    @typechecked
    def create(
            cls: Type['Block'],
            user: User,
            moves,
            commit: bool=True,
            echo: Optional[Callable]=None,
            sleep: Union[int, float]=0.0,
    ) -> Optional['Block']:
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
                block.difficulty = max(1, block.difficulty + 1)
            elif avg_timedelta > MAX_BLOCK_INTERVAL:
                block.difficulty = max(1, block.difficulty - 1)
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


def find_branch_point(
        node: Node, session, value: int, high: int
) -> int:
    if value > high:
        return 0
    mid = int((value + high) / 2)
    response = get(f"{node.url}{Node.get_blocks_endpoint}/{mid}")
    if response.status_code != 200:
        raise NodeUnavailable
    block = session.query(Block).get(mid)
    if (
            response.json()['block'] and block and
            block.hash == response.json()['block']['hash']
    ):
        if value == mid:
            return value
        return find_branch_point(node, session, mid, high)
    else:
        return find_branch_point(node, session, value, mid - 1)
