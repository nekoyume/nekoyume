"""
Models
======

`models.py` contains every relations regarding nekoyume blockchain and
game moves.
"""

import datetime
import hashlib
import os
import re

from bencode import bencode
from coincurve import PrivateKey, PublicKey
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from keccak import sha3_256
from requests import get, post
from requests.exceptions import ConnectionError, Timeout
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.sql.functions import char_length
from tablib import Dataset

from . import hashcash
from .exc import (InvalidBlockError,
                  InvalidMoveError,
                  InvalidNameError,
                  OutOfRandomError)
from .items import (Armor,
                    Combined,
                    Food,
                    Item,
                    Weapon,
                    get_related_items)


PROTOCOL_VERSION: int = 2
db = SQLAlchemy()
cache = Cache()


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
    except ConnectionError:
        return None
    except Timeout:
        return None
    if has_public_address:
        return f'http://{ip}{port}'
    else:
        return None


class Node(db.Model):
    """This object contains node information you know."""

    #: URL of node
    url = db.Column(db.String, primary_key=True)
    #: last connected datetime of the node
    last_connected_at = db.Column(db.DateTime, nullable=False, index=True)

    get_nodes_endpoint = '/nodes'
    post_node_endpoint = '/nodes'
    get_blocks_endpoint = '/blocks'
    post_block_endpoint = '/blocks'
    post_move_endpoint = '/moves'

    @classmethod
    def get(cls, url, session=db.session):
        get_node = Node.query.filter_by(url=url).first
        node = get_node()
        if node:
            return node
        elif get(f'{url}/ping').text == 'pong':
            node = Node(url=url, last_connected_at=datetime.datetime.utcnow())
            if session:
                session.add(node)
                try:
                    session.commit()
                except IntegrityError:
                    node = get_node()
                    if node is None:
                        raise
                    return node
            return node
        else:
            return None

    @classmethod
    def update(cls, node):
        """
        Update recent node list by scrapping other nodes' information.
        """
        try:
            response = get(f"{node.url}{Node.get_nodes_endpoint}")
        except (ConnectionError, Timeout):
            return
        for url in response.json()['nodes']:
            try:
                Node.get(url)
            except (ConnectionError, Timeout):
                continue
        db.session.commit()

    def ping(self):
        try:
            result = get(f'{self.url}/ping').text == 'pong'
            if result:
                self.last_connected_at = datetime.datetime.utcnow()
            return result
        except ConnectionError:
            return False
        except Timeout:
            return False

    @classmethod
    def broadcast(cls,
                  endpoint: str,
                  serialized_obj: dict,
                  sent_node=None,
                  my_node=None,
                  session=db.session) -> bool:
        """
        It broadcast `serialized_obj` to every nodes you know.

        :param        endpoint: endpoint of node to broadcast
        :param  serialized_obj: object that will be broadcasted.
        :param       sent_node: sent :class:`nekoyume.models.Node`.
                                this node ignore sent node.
        :param         my_node: my :class:`nekoyume.models.Node`.
                                received node ignore my node when they
                                broadcast received object.
        """

        for node in session.query(cls):
            if sent_node and sent_node.url == node.url:
                continue
            try:
                if my_node:
                    serialized_obj['sent_node'] = my_node.url
                post(node.url + endpoint, json=serialized_obj,
                     timeout=3)
                node.last_connected_at = datetime.datetime.utcnow()
                session.add(node)
            except ConnectionError:
                continue
            except Timeout:
                continue

        session.commit()
        return True


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
            if avg_timedelta <= datetime.timedelta(0, 5):
                valid = valid and self.difficulty == max(0, difficulty + 1)
            elif avg_timedelta > datetime.timedelta(0, 15):
                valid = valid and self.difficulty == max(0, difficulty - 1)
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

    def broadcast(self,
                  sent_node: bool=None,
                  my_node: bool=None,
                  session=db.session) -> bool:
        """
        It broadcast this block to every nodes you know.

       :param       sent_node: sent :class:`nekoyume.models.Node`.
                               this node ignore sent node.
       :param         my_node: my :class:`nekoyume.models.Node`.
                               received node ignore my node when they
                               broadcast received object.
        """
        return Node.broadcast(Node.post_block_endpoint,
                              self.serialize(False, True, True, True),
                              sent_node, my_node, session)

    @classmethod
    def sync(cls, node: Node=None, session=db.session, echo=None) -> bool:
        """
        Sync blockchain with other node.

        :param node: sync target :class:`nekoyume.models.Node`.
        """
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
                if (not node_last_block or
                   node_last_block['id'] < response.json()['block']['id']):
                    node_last_block = response.json()['block']
                    node = n
            except ConnectionError:
                continue
            except Timeout:
                continue

        last_block = session.query(Block).order_by(Block.id.desc()).first()

        if not node_last_block:
            return True

        #: If my chain is the longest one, we don't need to do anything.
        if last_block and last_block.id >= node_last_block['id']:
            return True

        def find_branch_point(value: int, high: int):
            mid = int((value + high) / 2)
            response = get((f"{node.url}{Node.get_blocks_endpoint}/"
                            f"{mid}"))
            block = session.query(Block).get(mid)
            if value > high:
                return 0
            if (response.json()['block'] and block and
               block.hash == response.json()['block']['hash']):
                if value == mid:
                        return value
                return find_branch_point(mid, high)
            else:
                return find_branch_point(value, mid - 1)

        if last_block:
            # TODO: Very hard to understand. fix this easily.
            if find_branch_point(last_block.id,
                                 last_block.id) == last_block.id:
                branch_point = last_block.id
            else:
                branch_point = find_branch_point(0, last_block.id)
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


def get_address(public_key: PublicKey) -> str:
    """Derive an Ethereum-style address from the given public key."""
    return '0x' + sha3_256(public_key.format(False)[1:]).hexdigest()[-40:]


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
            (char_length(user_address) == 42)
            # TODO: it should has proper test if 40-hex string
        ),
        db.CheckConstraint(char_length(user_public_key) == 33),
        db.CheckConstraint(
            (char_length(signature) >= 68) &
            (char_length(signature) <= 71)
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

    def broadcast(self, sent_node=None, my_node=None, session=db.session):
        """
        It broadcast this move to every nodes you know.

       :param       sent_node: sent :class:`nekoyume.models.Node`.
                               this node ignore sent node.
       :param         my_node: my :class:`nekoyume.models.Node`.
                               received node ignore my node when they
                               broadcast received object.
        """
        Node.broadcast(Node.post_move_endpoint,
                       self.serialize(False, True, True),
                       sent_node, my_node, session)

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
        result = result[int(self.block.difficulty / 4):]
        return result

    def roll(self, randoms: list, dice: str, combine=True):
        """
        Roll dices based on given randoms

            >>> from nekoyume.models import Move
            >>> move = Move()
            >>> move.roll([1, 7, 3], '2d6')
            6

        :params randoms: random numbers from
                         :func:`nekoyume.models.Move.get_randoms`
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

    def execute(self, avatar=None):
        if not avatar:
            avatar = Avatar.get(self.user_address, self.block_id - 1)
        if avatar.dead:
            raise InvalidMoveError
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, 'data/monsters.csv')
        monsters = Dataset().load(
            open(filename).read()
        ).dict
        randoms = self.get_randoms()
        monster = monsters[randoms.pop() % len(monsters)]
        battle_status = []

        for key in ('hp', 'piercing', 'armor'):
            monster[key] = int(monster[key])

        def get_item(ticker_name):
            items = get_related_items(Item)
            for item in items:
                if item.ticker_name == ticker_name:
                    return item
            return None

        weapon = armor = food = None
        if 'weapon' in self.details:
            weapon = get_item(self.details['weapon'])
        if 'armor' in self.details:
            armor = get_item(self.details['armor'])
        if 'food' in self.details:
            food = get_item(self.details['food'])

        while True:
            try:
                if (avatar.hp <= avatar.max_hp * 0.5
                   and food and food.ticker_name in avatar.items
                   and avatar.items[food.ticker_name] > 0):
                    avatar, status = food().execute(avatar)
                    battle_status.append(status)
                    avatar.items[food.ticker_name] -= 1
                    food = None

                if (avatar.hp <= avatar.max_hp * 0.2
                   and 'BNDG' in avatar.items and avatar.items['BNDG'] > 0):
                    rolled = self.roll(randoms, '2d6')
                    if rolled >= 7:
                        avatar.hp += 4
                        avatar.items['BNDG'] -= 1
                        battle_status.append({
                            'type': 'item_use',
                            'item': 'BNDG',
                            'status_change': 'HP +4'
                        })
                    else:
                        avatar.items['BNDG'] -= 1
                        battle_status.append({
                            'type': 'item_use_fail',
                            'item': 'BNDG',
                            'status_change': ''
                        })

                rolled = (self.roll(randoms, '2d6')
                          + avatar.modifier('strength'))
                if rolled >= 7:
                    damage = max(
                        self.roll(randoms, avatar.damage) - monster['armor'], 0
                    )
                    if weapon:
                        damage += weapon.attack_modifier(avatar, monster)
                    battle_status.append({
                        'type': 'attack_monster',
                        'damage': damage,
                        'monster': monster.copy(),
                    })
                    monster['hp'] = monster['hp'] - damage

                elif rolled in (2, 3, 4, 5, 6, 7, 8, 9):
                    monster_damage = self.roll(randoms, monster['damage'])
                    if armor:
                        monster_damage -= armor.armor_modifier(avatar, monster)
                    battle_status.append({
                        'type': 'attacked_by_monster',
                        'damage': monster_damage,
                        'monster': monster.copy(),
                    })
                    avatar.hp -= monster_damage
                    if rolled <= 6:
                        battle_status.append({
                            'type': 'get_xp',
                        })
                        avatar.xp += 1

                if monster['hp'] <= 0:
                    battle_status.append({
                        'type': 'kill_monster',
                        'monster': monster.copy(),
                    })
                    reward_code = self.roll(randoms, '1d10')
                    if len(monster[f'reward{reward_code}']):
                        avatar.get_item(monster[f'reward{reward_code}'])
                        battle_status.append({
                            'type': 'get_item',
                            'item': monster[f'reward{reward_code}'],
                        })
                    return (avatar, dict(
                        type='hack_and_slash',
                        result='win',
                        battle_status=battle_status,
                    ))

                if avatar.hp <= 0:
                    battle_status.append({
                        'type': 'killed_by_monster',
                        'monster': monster.copy(),
                    })
                    return (avatar, dict(
                        type='hack_and_slash',
                        result='lose',
                        battle_status=battle_status,
                    ))

            except OutOfRandomError:
                battle_status.append({
                    'type': 'run',
                    'monster': monster.copy(),
                })
                return (avatar, dict(
                    type='hack_and_slash',
                    result='finish',
                    battle_status=battle_status,
                ))


class Sleep(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'sleep',
    }

    def execute(self, avatar=None):
        if not avatar:
            avatar = Avatar.get(self.user_address, self.block_id - 1)
        avatar.hp = avatar.max_hp
        return avatar, dict(
            type='sleep',
            result='success',
        )


class CreateNovice(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'create_novice',
    }

    def execute(self, avatar=None):
        if avatar:
            #: Keep the information that should not be removed.
            gold = avatar.items['GOLD']
        else:
            gold = 0
        avatar = Novice()

        avatar.strength = int(self.details['strength'])
        avatar.dexterity = int(self.details['dexterity'])
        avatar.constitution = int(self.details['constitution'])
        avatar.intelligence = int(self.details['intelligence'])
        avatar.wisdom = int(self.details['wisdom'])
        avatar.charisma = int(self.details['charisma'])

        if (avatar.strength + avatar.dexterity + avatar.constitution +
           avatar.intelligence + avatar.wisdom + avatar.charisma) > 64:
            avatar.strength = 9
            avatar.dexterity = 9
            avatar.constitution = 9
            avatar.intelligence = 9
            avatar.wisdom = 9
            avatar.charisma = 9

        if 'name' in self.details:
            avatar.name = self.details['name']
        else:
            avatar.name = self.user_address[:6]

        if 'gravatar_hash' in self.details:
            avatar.gravatar_hash = self.details['gravatar_hash']
        else:
            avatar.gravatar_hash = 'HASH'

        avatar.user = self.user_address
        avatar.current_block = self.block
        avatar.hp = avatar.max_hp
        avatar.xp = 0
        avatar.lv = 1
        avatar.items = dict(
            GOLD=gold
        )

        return (avatar, dict(
            type='create_novice',
            result='success',
        ))


class LevelUp(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'level_up',
    }

    def execute(self, avatar=None):
        if not avatar:
            avatar = Avatar.get(self.user_address, self.block_id - 1)
        if avatar.xp < avatar.lv + 7:
            return avatar, dict(
                type='level_up',
                result='failed',
                message="You don't have enough xp.",
            )

        avatar.xp -= avatar.lv + 7
        avatar.lv += 1
        setattr(avatar, self.details['new_status'],
                getattr(avatar, self.details['new_status']) + 1)
        if self.details['new_status'] == 'constitution':
            avatar.hp += 1
        return avatar, dict(
            type='level_up',
            result='success',
        )


class Say(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'say',
    }

    def execute(self, avatar=None):
        if not avatar:
            avatar = Avatar.get(self.user_address, self.block_id - 1)

        return avatar, dict(
            type='say',
            message=self.details['content'],
        )


class Send(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'send',
    }

    def execute(self, avatar=None):
        if not avatar:
            avatar = Avatar.get(self.user_address, self.block_id - 1)

        if int(self.details['amount']) <= 0:
            return avatar, dict(
                type='send',
                result='fail',
                message="You can't send items with a negative or zero amount."
            )

        if (self.details['item_name'] not in avatar.items or
           avatar.items[self.details['item_name']]
           - int(self.details['amount']) < 0):
            return avatar, dict(
                type='send',
                result='fail',
                message="You don't have enough items to send."
            )

        avatar.items[self.details['item_name']] -= int(self.details['amount'])
        return avatar, dict(
            type='send',
            result='success',
        )

    def receive(self, receiver=None):
        if not receiver:
            receiver = Avatar.get(self.details['receiver'], self.block_id - 1)

        for i in range(int(self.details['amount'])):
            receiver.get_item(self.details['item_name'])

        return receiver, dict(
            type='receive',
            result='success',
        )


class Combine(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'combine',
    }

    def execute(self, avatar=None):
        if not avatar:
            avatar = Avatar.get(self.user_address, self.block_id - 1)
        if avatar.items['GOLD'] <= 0:
            return avatar, dict(
                type='combine',
                result='failure',
                reason='insufficient_gold'
            )
        for i in ('item1', 'item2', 'item3'):
            if (self.details[i] not in avatar.items or
               avatar.items[self.details[i]] <= 0):
                return avatar, dict(
                    type='combine',
                    result='failure',
                    reason='insufficient_item'
                )
        randoms = self.get_randoms()
        recipes = {scls.ticker_name: scls.recipe
                   for scls in Combined.__subclasses__()}
        dices = {scls.ticker_name: scls.dice
                 for scls in Combined.__subclasses__()}
        for result, recipe in recipes.items():
            if recipe == {self.details['item1'],
                          self.details['item2'],
                          self.details['item3']}:
                avatar.items[self.details['item1']] -= 1
                avatar.items[self.details['item2']] -= 1
                avatar.items[self.details['item3']] -= 1
                avatar.items['GOLD'] -= 1
                if self.roll(randoms, dices[result]) == 1:
                    avatar.get_item(result)
                    return avatar, dict(
                        type='combine',
                        result='success',
                        result_item=result,
                    )
                else:
                    return avatar, dict(
                        type='combine',
                        result='failure',
                        reason='bad_luck'
                    )

        return avatar, dict(
            type='combine',
            result='failure',
            reason='no_combination'
        )


class Sell(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'sell',
    }


class Buy(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'buy',
    }


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

    def send(self, item_name, amount, receiver):
        if self.avatar().items[item_name] < int(amount) or int(amount) <= 0:
            raise InvalidMoveError

        return self.move(Send(details={
            'item_name': item_name,
            'amount': amount,
            'receiver': receiver,
        }))

    def sell(self, item_name, price):
        return self.move(Sell(details={'item_name': item_name,
                                       'price': price}))

    def buy(self, move_id):
        return self.move(Buy(details={'move_id': move_id}))

    def create_novice(self, details):
        return self.move(CreateNovice(details=details))

    def level_up(self, new_status):
        return self.move(LevelUp(details={
            'new_status': new_status,
        }))

    def say(self, content):
        return self.move(Say(details={'content': content}))

    def combine(self, item1, item2, item3):
        return self.move(Combine(details={'item1': item1,
                                          'item2': item2,
                                          'item3': item3}))

    def create_block(self, moves, commit=True, echo=None):
        """ Create a block. """
        for move in moves:
            if not move.valid:
                raise InvalidMoveError(move)
        block = Block(version=PROTOCOL_VERSION)
        block.root_hash = hashlib.sha256(
            ''.join(sorted((m.id for m in moves))).encode('utf-8')
        ).hexdigest()
        block.creator = self.address
        block.created_at = datetime.datetime.utcnow()

        prev_block = self.session.query(Block).order_by(
            Block.id.desc()
        ).first()
        if prev_block:
            block.id = prev_block.id + 1
            block.prev_hash = prev_block.hash
            block.difficulty = prev_block.difficulty
            difficulty_check_block = self.session.query(Block).get(
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
            if avg_timedelta <= datetime.timedelta(0, 5):
                block.difficulty = max(0, block.difficulty + 1)
            elif avg_timedelta > datetime.timedelta(0, 15):
                block.difficulty = max(0, block.difficulty - 1)
        else:
            #: Genesis block
            block.id = 1
            block.prev_hash = None
            block.difficulty = 0

        block.suffix = hashcash._mint(block.serialize(), bits=block.difficulty)
        if self.session.query(Block).get(block.id):
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
                self.session.add(block)
                self.session.commit()
            except IntegrityError:
                return None

        return block

    def avatar(self, block_id=None):
        """
        get avatar of the user.

        :params block_id: Avatar's block timing. If None, it sets last block.
        """
        if not block_id:
            block = self.session.query(Block).order_by(
                Block.id.desc()).first()
            if block:
                block_id = block.id
            else:
                block_id = 0
        return Avatar.get(self.address, block_id)


class Avatar():
    @classmethod
    @cache.memoize(timeout=0)
    def get(cls, user_addr, block_id, session=db.session):
        """
        get avatar.

        :params user_addr: Avatar's user address
        :params  block_id: Avatar's block timing
        :params   session: Database session to get data
        """
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
        avatar.items['GOLD'] += session.query(Block).filter_by(
            creator=user_addr
        ).filter(Block.id <= block_id).count() * 8

        for move in moves:
            if move.user_address == user_addr:
                avatar, result = move.execute(avatar)
            if (type(move) == Send and
               move.details['receiver'] == user_addr):
                avatar, result = move.receive(avatar)

        return avatar

    def modifier(self, status):
        """ Return modifier of the status. """
        status = getattr(self, status)
        if status in (1, 2, 3):
            return -3
        elif status in (4, 5):
            return -2
        elif status in (6, 7, 8):
            return -1
        elif status in (9, 10, 11, 12):
            return 0
        elif status in (13, 14, 15):
            return 1
        elif status in (16, 17):
            return 2
        elif status >= 18:
            return 3
        return 0

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
    def damage(self):
        raise NotImplementedError

    @property
    def max_hp(self):
        raise NotImplementedError

    @property
    def profile_image_url(self):
        return f'https://www.gravatar.com/avatar/{self.gravatar_hash}?d=mm'

    @property
    def weapons(self) -> list:
        result = []
        for weapon in get_related_items(Weapon):
            if (weapon.ticker_name in self.items.keys() and
               self.items[weapon.ticker_name] > 0):
                result.append(weapon)

        return result

    @property
    def last_weapon(self) -> Weapon:
        last_has = HackAndSlash.query.filter_by(
            user_address=self.user_address
        ).order_by(HackAndSlash.block_id.desc()).first()

        if last_has:
            try:
                return last_has.details['weapon']
            except KeyError:
                return None
        else:
            return None

    @property
    def last_armor(self) -> Armor:
        last_has = HackAndSlash.query.filter_by(
            user_address=self.user_address
        ).order_by(HackAndSlash.block_id.desc()).first()

        if last_has:
            try:
                return last_has.details['armor']
            except KeyError:
                return None
        else:
            return None

    @property
    def armors(self) -> list:
        result = []
        for armor in get_related_items(Armor):
            if (armor.ticker_name in self.items.keys() and
               self.items[armor.ticker_name] > 0):
                result.append(armor)

        return result

    @property
    def foods(self) -> list:
        result = []
        for food in get_related_items(Food):
            if (food.ticker_name in self.items.keys() and
               self.items[food.ticker_name] > 0):
                result.append(food)

        return result

    @property
    def dead(self) -> bool:
        return self.hp <= 0


class Novice(Avatar):
    @property
    def damage(self):
        return '1d6'

    @property
    def max_hp(self):
        return self.constitution + 6
