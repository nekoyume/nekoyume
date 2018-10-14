from dataclasses import dataclass, field
import datetime
from typing import List

from coincurve import PrivateKey, PublicKey
from flask_caching import Cache
from sqlalchemy import or_

from .battle.enums import ItemType
from .exc import InvalidMoveError, InvalidNameError
from .items import Item
from .move import (
    Buy,
    CreateNovice,
    FirstClass,
    HackAndSlash,
    LevelUp,
    Move,
    MoveDetail,
    MoveZone,
    Say,
    Sell,
    Send,
    Sleep
)
from .orm import db
from .tables import Tables
from .util import get_address


cache = Cache()


class User():
    """ It contains user's keys and avatar information. """

    private_key: PrivateKey
    public_key: PublicKey

    def __init__(self, private_key: PrivateKey, session=db.session):
        if not isinstance(private_key, PrivateKey):
            raise TypeError(
                f'private_key must be an instance of {PrivateKey.__module__}.'
                f'{PrivateKey.__qualname__}, not {private_key!r}'
            )
        self.private_key = private_key
        self.public_key: PublicKey = private_key.public_key
        self.session = session

    @property
    def address(self) -> str:
        """ It returns address of the user. """
        return get_address(self.public_key)

    def sign(self, move: Move) -> None:
        """ put signature into the given move using the user's private key. """
        if move.name is None:
            raise InvalidNameError
        move.user_public_key = self.public_key.format(compressed=True)
        move.user_address = self.address
        serialized = move.serialize(include_signature=False)
        move.signature = self.private_key.sign(
            serialized
        )
        move.id = move.hash

    @property
    def moves(self):
        """ return the user's moves. """
        return self.session.query(Move).filter(
            Move.user_public_key == self.public_key.format(compressed=True),
            Move.block != None,  # noqa: E711
        ).order_by(Move.block_id.desc())

    def move(self, new_move, tax=0, commit=True):
        """
        make a move of the user.

        :params new_move: Move object to make
        :params      tax: Tax to apply
        :params   commit: commit in this function automatically or not
        """
        new_move.tax = tax
        new_move.created_at = datetime.datetime.utcnow()
        self.sign(new_move)

        if new_move.valid:
            if commit:
                self.session.add(new_move)
                self.session.commit()
        else:
            raise InvalidMoveError

        return new_move

    def hack_and_slash(self, weapon=None, armor=None, food=None):
        details = dict()
        if weapon:
            details['weapon'] = weapon
        if armor:
            details['armor'] = armor
        if food:
            details['food'] = food
        return self.move(HackAndSlash(details=details))

    def sleep(self, spot=''):
        return self.move(Sleep())

    def send(self, item_index, amount, receiver):
        item = self.avatar.items[item_index]
        if item.amount < int(amount) or int(amount) <= 0:
            raise InvalidMoveError

        return self.move(Send(details={
            'item_index': item_index,
            'amount': amount,
            'receiver': receiver,
        }))

    def sell(self, item_index, price):
        return self.move(Sell(details={'item_index': item_index,
                                       'price': price}))

    def buy(self, move_id):
        return self.move(Buy(details={'move_id': move_id}))

    def create_novice(self, details):
        return self.move(CreateNovice(details=details))

    def first_class(self, class_):
        return self.move(FirstClass(details={'class': class_}))

    def move_zone(self, zone):
        return self.move(MoveZone(details={'zone': zone}))

    def level_up(self, new_status):
        return self.move(LevelUp(details={
            'new_status': new_status,
        }))

    def say(self, content):
        return self.move(Say(details={'content': content}))

    def avatar(self, block_id=None):
        """
        get avatar of the user.

        :params block_id: Avatar's block timing. If None, it sets last block.
        """
        if not block_id:
            from .block import Block
            block = self.session.query(Block).order_by(
                Block.id.desc()).first()
            if block:
                block_id = block.id
            else:
                block_id = 0
        return Avatar.get(self.address, block_id)


@dataclass
class Avatar:
    name: str
    user: str
    current_block: 'Block'
    class_: str  # noqa
    level: int = 1
    gold: int = 0
    exp: int = 0
    exp_max: int = 0
    hp: int = 0
    hp_max: int = 0
    strength: int = 0
    dexterity: int = 0
    intelligence: int = 0
    constitution: int = 0
    luck: int = 0
    items: List[Item] = field(default_factory=list)
    zone: str = ''
    gravatar_hash: str = 'HASH'

    @classmethod
    @cache.memoize(timeout=0)
    def get(cls, user_addr, block_id, session=db.session):
        """
        get avatar.

        :params user_addr: Avatar's user address
        :params  block_id: Avatar's block timing
        :params   session: Database session to get data
        """
        from .block import Block
        create_move = session.query(Move).filter(
            Move.user_address == user_addr,
            Move.block_id <= block_id
        ).order_by(
            Move.block_id.desc()
        ).filter(
            Move.name.like('create_%')
        ).first()
        if not create_move or block_id < create_move.block_id:
            return None
        moves = session.query(Move).filter(
            or_(Move.user_address == user_addr, Move.id.in_(
                    db.session.query(MoveDetail.move_id).filter_by(
                        key='receiver', value=user_addr)))
        ).filter(
            Move.block_id >= create_move.block_id,
            Move.block_id <= block_id
        ).order_by(Move.block_id.asc())
        avatar, result = create_move.execute(None)
        gold_added = session.query(Block).filter_by(
            creator=user_addr
        ).filter(Block.id <= block_id).count() * 8
        avatar.gold += gold_added

        for move in moves:
            if move.user_address == user_addr:
                avatar, result = move.execute(avatar)
            if (type(move) == Send and
               move.details['receiver'] == user_addr):
                avatar, result = move.receive(avatar)

        return avatar

    def get_item(self, item):
        """
        Get given item.

        :params item: item's ticker name
        """
        if item not in self.items:
            self.items[item] = 1
        else:
            self.items[item] += 1

    @property
    def profile_image_url(self):
        return f'https://www.gravatar.com/avatar/{self.gravatar_hash}?d=mm'

    @property
    def weapons(self) -> list:
        return [item for item in self.items if item.type_ == ItemType.WEAPON]

    @property
    def last_weapon(self):
        last_has = HackAndSlash.query.filter_by(
            user_address=self.user
        ).order_by(HackAndSlash.block_id.desc()).first()

        if last_has:
            weapon = last_has.details.get('weapon')
            if weapon:
                return int(weapon)
        return None

    @property
    def armors(self) -> list:
        return [item for item in self.items if item.type_ == ItemType.ARMOR]

    @property
    def last_armor(self):
        last_has = HackAndSlash.query.filter_by(
            user_address=self.user
        ).order_by(HackAndSlash.block_id.desc()).first()

        if last_has:
            armor = last_has.details.get('armor')
            if armor:
                return int(armor)
        return None

    @property
    def foods(self) -> list:
        return [item for item in self.items if item.type_ == ItemType.FOOD]

    @property
    def dead(self) -> bool:
        return self.hp <= 0

    @property
    def unlocked_zone(self) -> list:
        zone_list = []
        for (k, v) in Tables.zone.items():
            if self.level >= v.unlock_level:
                zone_list.append(k)
        return zone_list
