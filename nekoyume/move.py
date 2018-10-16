"""
Move
====

`move.py` contains every relations regarding nekoyume blockchain and
game moves.
"""
import datetime
import hashlib
import os
import random
import re

from bencode import bencode
from coincurve import PublicKey
from requests import get
from requests.exceptions import ConnectionError, Timeout
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection

from .battle.characters import Factory as CharacterFactory
from .battle.simul import Simulator
from .exc import InvalidMoveError, OutOfRandomError
from .orm import db
from .tables import Tables
from .util import ensure_block, get_address


NUM_HACK_AND_SLASH_MONSTERS: int = 3


def get_my_public_url():
    if 'PUBLIC_URL' in os.environ:
        return os.environ['PUBLIC_URL']
    try:
        if os.environ.get('PORT', '80') != '80':
            port = ':' + os.environ.get('PORT', '80')
        else:
            port = ''
        ip = get('http://ip.42.pl/raw').text
        has_public_address = get(
            f'http://{ip}{port}/ping'
        ).text == 'pong'
    except (ConnectionError, Timeout):
        return None
    if has_public_address:
        return f'http://{ip}{port}'
    else:
        return None


class Move(db.Model):
    """This object contain general move information."""
    __tablename__ = 'move'
    #: move's hash
    id = db.Column(db.String, primary_key=True)
    #: move's block id. if the move isn't confirmed yet, this will be null
    block_id = db.Column(db.Integer, db.ForeignKey('block.id'),
                         nullable=True, index=True)
    #: move's block
    block = db.relationship('Block', uselist=False, backref='moves')
    #: 33 bytes long form (i.e., compressed from) of user's public key.
    user_public_key = db.Column(db.LargeBinary, nullable=False, index=True)
    #: user's address ("0x"-prefixed 40 hexdecimal string; total 42 chars)
    user_address = db.Column(db.String, nullable=False, index=True)
    #: move's signature (71 bytes)
    signature = db.Column(db.LargeBinary, nullable=False)
    #: move name
    name = db.Column(db.String, nullable=False, index=True)
    #: move details. it contains parameters of move
    details = association_proxy(
        'move_details', 'value',
        creator=lambda k, v: MoveDetail(key=k, value=v)
    )
    #: move tax (not implemented yet)
    tax = db.Column(db.BigInteger, default=0, nullable=False)
    #: move creation datetime.
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint(
            db.func.lower(user_address).like('0x%') &
            (db.func.length(user_address) == 42)
            # TODO: it should has proper test if 40-hex string
        ),
        db.CheckConstraint(db.func.length(user_public_key) == 33),
        db.CheckConstraint(
            (db.func.length(signature) >= 68) &
            (db.func.length(signature) <= 71)
        ),
    )
    __mapper_args__ = {
        'polymorphic_identity': 'move',
        'polymorphic_on': name,
    }

    @classmethod
    def deserialize(cls, serialized: dict, block_id=None) -> 'Move':
        if block_id is None and serialized.get('block'):
            block_id = serialized['block'].get('id')
        return cls(
            id=serialized['id'],
            user_address=serialized['user_address'],
            name=serialized['name'],
            user_public_key=bytes.fromhex(serialized['user_public_key']),
            signature=bytes.fromhex(serialized['signature']),
            tax=serialized['tax'],
            details=serialized['details'],
            created_at=datetime.datetime.strptime(
                serialized['created_at'],
                '%Y-%m-%d %H:%M:%S.%f'),
            block_id=block_id,
        )

    @property
    def valid(self):
        """Check if this object is valid or not"""
        if not self.signature:
            return False

        assert isinstance(self.signature, bytes)
        assert 68 <= len(self.signature) <= 71
        assert isinstance(self.user_public_key, bytes)
        assert len(self.user_public_key) == 33
        assert isinstance(self.user_address, str)
        assert re.match(r'^(?:0[xX])?[0-9a-fA-F]{40}$', self.user_address)
        public_key = PublicKey(self.user_public_key)
        verified = public_key.verify(
            self.signature,
            self.serialize(include_signature=False),
        )
        if not verified:
            return False

        if get_address(public_key) != self.user_address:
            return False

        return self.id == self.hash

    @property
    def confirmed(self):
        """Check if this object is confirmed or not"""
        return self.block and self.block.hash is not None

    def serialize(self,
                  use_bencode=True,
                  include_signature=False,
                  include_id=False,
                  include_block=False):
        """
        This function serialize block.

        :param       use_bencode: check if you want to encode using bencode.
        :param include_signature: check if you want to include signature.
        :param        include_id: check if you want to include linked moves.
        :param     include_block: check if you want to include block.
        """
        binary = (lambda x: x) if use_bencode else bytes.hex
        serialized = dict(
            user_address=self.user_address,
            name=self.name,
            details={k: str(v) for k, v in dict(self.details).items()},
            tax=self.tax,
            created_at=str(self.created_at),
        )
        if include_signature:
            serialized.update(
                signature=binary(self.signature),
                user_public_key=binary(self.user_public_key),
            )
        if include_id:
            serialized['id'] = self.id
        if include_block:
            if self.block:
                serialized['block'] = self.block.serialize(False)
            else:
                serialized['block'] = None
        if use_bencode:
            serialized = bencode(serialized)
        return serialized

    @property
    def hash(self) -> str:
        """ Get move hash """
        return hashlib.sha256(
            self.serialize(include_signature=True)
        ).hexdigest()

    def get_randoms(self) -> list:
        """ get random numbers by :doc:`Hash random <white_paper>` """
        if not (self.block and self.block.hash and self.id):
            return []
        result = [ord(a) ^ ord(b) for a, b in zip(self.block.hash, self.id)]
        result = result[self.block.difficulty // 4:]
        return result

    def make_random_generator(self) -> random.Random:
        if self.block and self.block.hash and self.id:
            bh = bytes.fromhex(self.block.hash)
            mi = bytes.fromhex(self.id)
            seed = bytes(a ^ b for a, b in zip(bh, mi))
        else:
            seed = 0
        return random.Random(seed)

    def roll(self, randoms: list, dice: str, combine=True):
        """
        Roll dices based on given randoms

            >>> from nekoyume.move import Move
            >>> move = Move()
            >>> move.roll([1, 7, 3], '2d6')
            6

        :params randoms: random numbers from
                         :func:`nekoyume.move.Move.get_randoms`
        :params    dice: dice to roll (e.g. 2d6)
        :params combine: return combined result or not if rolling it multiple.
        """
        result = []
        if dice.find('+') > 0:
            dice, plus = dice.split('+')
            plus = int(plus)
        else:
            plus = 0
        cnt, dice_type = (int(i) for i in dice.split('d'))
        for i in range(cnt):
            try:
                result.append(randoms.pop() % dice_type + 1)
            except IndexError:
                raise OutOfRandomError
        if combine:
            return sum(result) + plus
        else:
            return result

    @ensure_block
    def execute(self):
        raise NotImplementedError()


class MoveDetail(db.Model):
    """ This object contains move's key/value information. """

    #: move id
    move_id = db.Column(db.String,  db.ForeignKey('move.id'),
                        nullable=True, primary_key=True)
    move = db.relationship(Move, backref=db.backref(
        'move_details',
        collection_class=attribute_mapped_collection("key"),
        cascade="all, delete-orphan"
    ))
    #: MoveDetail's key
    key = db.Column(db.String, nullable=False, primary_key=True)
    #: MoveDetail's value
    value = db.Column(db.String, nullable=False, index=True)


class HackAndSlash(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'hack_and_slash',
    }

    @ensure_block
    def execute(self, avatar=None):
        if not avatar:
            from .user import Avatar
            avatar = Avatar.get(self.user_address, self.block_id - 1)
        if avatar.dead:
            raise InvalidMoveError
        # TODO Load other users avatar
        rand = self.make_random_generator()
        simul = Simulator(rand, avatar.zone)

        factory = CharacterFactory()
        my_character = factory.create_from_avatar(
            avatar, self.details)
        simul.characters.append(my_character)
        appear_monsters = Tables.get_monster_appear_list(avatar.zone)
        for i in range(NUM_HACK_AND_SLASH_MONSTERS):
            simul.characters.append(
                factory.create_monster(appear_monsters.select(rand)))
        simul.simulate()

        my_character.to_avatar(avatar)

        return (avatar, dict(
                    type='hack_and_slash',
                    result=simul.result,
                    battle_logger=simul.logger,
                ))


class Sleep(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'sleep',
    }

    @ensure_block
    def execute(self, avatar=None):
        if not avatar:
            from .user import Avatar
            avatar = Avatar.get(self.user_address, self.block_id - 1)
        avatar.hp = avatar.hp_max
        return avatar, dict(
            type='sleep',
            result='success',
        )


class CreateNovice(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'create_novice',
    }

    @ensure_block
    def execute(self, avatar=None):
        from .user import Avatar
        gold = getattr(avatar, 'gold', 0)

        name = self.details.get('name', '')[:10] + '#' + self.user_address[:6]
        avatar = Avatar(
            name=name,
            user=self.user_address,
            current_block=self.block,
            gold=gold,
            class_='novice',
            level=1,
            zone=list(Tables.zone.keys())[0],
            gravatar_hash=self.details.get('gravatar_hash', 'HASH'),
        )

        factory = CharacterFactory()
        character = factory.create_from_avatar(avatar, self.details)
        character.to_avatar(avatar, hp_recover=True)

        return (avatar, dict(
            type='create_novice',
            result='success',
        ))


class FirstClass(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'first_class',
    }

    @ensure_block
    def execute(self, avatar=None):
        if not avatar:
            from .user import Avatar
            avatar = Avatar.get(self.user_address, self.block_id - 1)
        if avatar.class_ != 'novice':
            return avatar, dict(
                type='first_class',
                result='failed',
                message="Already change class.",
            )
        avatar.class_ = self.details['class']
        return avatar, dict(
            type='first_class',
            result='success',
        )


class MoveZone(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'move_zone',
    }

    @ensure_block
    def execute(self, avatar=None):
        if not avatar:
            from .user import Avatar
            avatar = Avatar.get(self.user_address, self.block_id - 1)
        zone = self.details['zone']
        if zone not in Tables.zone:
            return avatar, dict(
                type='move_zone',
                result='failed',
                message="Invalid zone.",
            )
        avatar.zone = zone
        return avatar, dict(
            type='move_zone',
            result='success',
        )


class LevelUp(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'level_up',
    }

    @ensure_block
    def execute(self, avatar=None):
        if not avatar:
            from .user import Avatar
            avatar = Avatar.get(self.user_address, self.block_id - 1)
        exp_max = Tables.get_exp_max(avatar.level)
        if exp_max == 0:
            return avatar, dict(
                type='level_up',
                result='failed',
                message="Max level.",
            )
        if avatar.exp < exp_max:
            return avatar, dict(
                type='level_up',
                result='failed',
                message="You don't have enough exp.",
            )
        avatar.exp -= exp_max
        avatar.level += 1
        setattr(avatar, self.details['new_status'],
                getattr(avatar, self.details['new_status']) + 1)
        return avatar, dict(
            type='level_up',
            result='success',
        )


class Say(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'say',
    }

    @ensure_block
    def execute(self, avatar=None):
        if not avatar:
            from .user import Avatar
            avatar = Avatar.get(self.user_address, self.block_id - 1)

        return avatar, dict(
            type='say',
            message=self.details['content'],
        )


class Send(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'send',
    }

    @ensure_block
    def execute(self, avatar=None):
        if not avatar:
            from .user import Avatar
            avatar = Avatar.get(self.user_address, self.block_id - 1)

        if int(self.details['amount']) <= 0:
            return avatar, dict(
                type='send',
                result='fail',
                message="You can't send items with a negative or zero amount."
            )

        if (self.details['item_index'] not in avatar.items or
           avatar.items[self.details['item_index']]
           - int(self.details['amount']) < 0):
            return avatar, dict(
                type='send',
                result='fail',
                message="You don't have enough items to send."
            )

        avatar.items[self.details['item_index']] -= int(self.details['amount'])
        return avatar, dict(
            type='send',
            result='success',
        )

    def receive(self, receiver=None):
        if not receiver:
            from .user import Avatar
            receiver = Avatar.get(self.details['receiver'], self.block_id - 1)

        for i in range(int(self.details['amount'])):
            receiver.get_item(self.details['item_name'])

        return receiver, dict(
            type='receive',
            result='success',
        )


class Sell(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'sell',
    }


class Buy(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'buy',
    }
