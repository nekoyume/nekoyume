import datetime
from hashlib import sha256 as h

from bencode import bencode
from flask_cache import Cache
from flask_sqlalchemy import SQLAlchemy
import requests
import seccure
from sqlalchemy import or_
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection
import tablib

from exc import (InvalidBlockError,
                 InvalidMoveError,
                 InvalidNameError,
                 OutOfRandomError)
import hashcash


db = SQLAlchemy()
cache = Cache()


class Node(db.Model):
    url = db.Column(db.String, primary_key=True)
    last_connected_at = db.Column(db.DateTime, nullable=False, index=True)

    get_blocks_endpoint = '/blocks'
    post_block_endpoint = '/blocks'
    post_move_endpoint = '/moves'

    @classmethod
    def broadcast(cls, endpoint, serialized_obj, sent_node=None, my_node=None):
        for node in cls.query:
            if sent_node and sent_node.url == node.url:
                continue
            try:
                if my_node:
                    serialized_obj['sent_node'] = my_node.url
                requests.post(node.url + endpoint,
                              json=serialized_obj)
                node.last_connected_at = datetime.datetime.now()
                db.session.add(node)
            except requests.exceptions.ConnectionError:
                continue
        db.session.commit()


class Block(db.Model):
    __tablename__ = 'block'
    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String, nullable=False, index=True, unique=True)
    prev_hash = db.Column(db.String,
                          index=True)
    creator = db.Column(db.String, nullable=False, index=True)
    root_hash = db.Column(db.String, nullable=False)
    suffix = db.Column(db.String, nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.now())

    @property
    def valid(self):
        return (self.hash ==
                h(
                    (self.serialize() + self.suffix.encode('utf-8'))
                ).hexdigest())

    def serialize(self, use_bencode=True,
                  include_suffix=False,
                  include_moves=False,
                  include_hash=False):
        serialized = dict(
            id=self.id,
            creator=self.creator,
            prev_hash=self.prev_hash,
            difficulty=self.difficulty,
            root_hash=self.root_hash,
            created_at=str(self.created_at),
        )
        if include_suffix:
            serialized['suffix'] = self.suffix

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

    def broadcast(self, sent_node=None, my_node=None):
        Node.broadcast(Node.post_block_endpoint,
                       self.serialize(False, True, True, True),
                       sent_node, my_node)

    @classmethod
    def sync(cls, node):
        response = requests.get(f"{node.url}{Node.get_blocks_endpoint}/last")
        last_block = Block.query.order_by(Block.id.desc()).first()

        #: If my chain is the longest one, we don't need to do anything.
        if last_block and last_block.id >= response.json()['block']['id']:
            return True

        def find_branch_point(value, high):
            mid = int((value + high) / 2)
            response = requests.get((f"{node.url}{Node.get_blocks_endpoint}/"
                                     f"{mid}"))
            if value > high:
                return 0
            if response.json()['block']:
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

        for block in Block.query.filter(Block.id > branch_point):
            for move in block.moves:
                move.block_id = None
            db.session.delete(block)

        response = requests.get(f"{node.url}{Node.get_blocks_endpoint}",
                                params={'from': branch_point + 1})

        for new_block in response.json()['blocks']:
            block = Block()
            block.id = new_block['id']
            block.creator = new_block['creator']
            block.created_at = datetime.datetime.strptime(
                new_block['created_at'], '%Y-%m-%d %H:%M:%S.%f')
            block.prev_hash = new_block['prev_hash']
            block.hash = new_block['hash']
            block.difficulty = new_block['difficulty']
            block.suffix = new_block['suffix']
            block.root_hash = new_block['root_hash']

            for new_move in new_block['moves']:
                move = Move.query.get(new_move['id'])
                if not move:
                    move = Move(
                        id=new_move['id'],
                        user=new_move['user'],
                        name=new_move['name'],
                        signature=new_move['signature'],
                        tax=new_move['tax'],
                        details=new_move['details'],
                        created_at=datetime.datetime.strptime(
                            new_move['created_at'],
                            '%Y-%m-%d %H:%M:%S.%f'),
                        block_id=block.id,
                    )
                if not move.valid:
                    db.session.rollback()
                    raise InvalidMoveError
                block.moves.append(move)

            if not block.valid:
                db.session.rollback()
                raise InvalidBlockError
            db.session.add(block)

        db.session.commit()
        return True


class Move(db.Model):
    __tablename__ = 'move'
    id = db.Column(db.String, primary_key=True)
    block_id = db.Column(db.Integer, db.ForeignKey('block.id'),
                         nullable=True, index=True)
    block = db.relationship('Block', uselist=False, backref='moves')
    user = db.Column(db.String, nullable=False, index=True)
    signature = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False, index=True)
    details = association_proxy(
        'move_details', 'value',
        creator=lambda k, v: MoveDetail(key=k, value=v)
    )
    tax = db.Column(db.BigInteger, default=0, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.now())

    __mapper_args__ = {
        'polymorphic_identity': 'move',
        'polymorphic_on': name,
    }

    @property
    def valid(self):
        if not self.signature or self.signature.find(' ') < 0:
            return False

        public_key = self.signature.split(' ')[1]
        valid = True

        valid = valid and seccure.verify(
            self.serialize(include_signature=False),
            self.signature.split(' ')[0],
            public_key,
        )
        valid = valid and (
            self.user == h(public_key.encode('utf-8')).hexdigest()[:30]
        )

        valid = valid and (self.id == self.hash)

        return valid

    @property
    def confirmed(self):
        return self.block and self.block.hash is not None

    def serialize(self,
                  use_bencode=True,
                  include_signature=False,
                  include_id=False):
        serialized = dict(
            user=self.user,
            name=self.name,
            details=dict(self.details),
            tax=self.tax,
            created_at=str(self.created_at),
        )
        if include_signature:
            serialized['signature'] = self.signature
        if include_id:
            serialized['id'] = self.id
        if use_bencode:
            serialized = bencode(serialized)
        return serialized

    def broadcast(self, sent_node=None, my_node=None):
        Node.broadcast(Node.post_move_endpoint,
                       self.serialize(False, True, True),
                       sent_node, my_node)

    @property
    def hash(self):
        return h(self.serialize(include_signature=True)).hexdigest()

    def get_randoms(self):
        if not (self.block and self.block.hash and self.id):
            return []
        result = [ord(a) ^ ord(b) for a, b in zip(self.block.hash, self.id)]
        result = result[int(self.block.difficulty / 4):]
        return result

    def roll(self, randoms, dice, sum_=True):
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
        if sum_:
            return sum(result) + plus
        else:
            return result


class MoveDetail(db.Model):
    move_id = db.Column(db.String,  db.ForeignKey('move.id'),
                        nullable=True, primary_key=True)
    move = db.relationship(Move, backref=db.backref(
        'move_details',
        collection_class=attribute_mapped_collection("key"),
        cascade="all, delete-orphan"
    ))
    key = db.Column(db.String, nullable=False, primary_key=True)
    value = db.Column(db.String, nullable=False, index=True)


class HackAndSlash(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'hack_and_slash',
    }

    def execute(self, avatar=None):
        if not avatar:
            avatar = Avatar.get(self.user, self.block_id - 1)
        monsters = tablib.Dataset().load(
            open('data/monsters.csv').read()
        ).dict
        randoms = self.get_randoms()
        monster = monsters[randoms.pop() % len(monsters)]
        battle_status = []

        for key in ('hp', 'piercing', 'armor'):
            monster[key] = int(monster[key])

        while True:
            try:
                rolled = (self.roll(randoms, '2d6')
                          + avatar.modifier('strength'))
                if rolled >= 7:
                    damage = max(
                        self.roll(randoms, avatar.damage) - monster['armor'], 0
                    )
                    battle_status.append({
                        'type': 'attack_monster',
                        'damage': damage,
                        'monster': monster.copy(),
                    })
                    monster['hp'] = monster['hp'] - damage

                elif rolled in (2, 3, 4, 5, 6, 7, 8, 9):
                    monster_damage = self.roll(randoms, monster['damage'])
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
                    if self.roll(randoms, '2d6') >= 10:
                        avatar.get_item('Bandages')
                        battle_status.append({
                            'type': 'get_item',
                            'item': 'Bandages',
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
            avatar = Avatar.get(self.user, self.block_id - 1)
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
            coin = avatar.items['Coin']
        else:
            coin = 0
        avatar = Novice()

        avatar.strength = int(self.details['strength'])
        avatar.dexterity = int(self.details['dexterity'])
        avatar.constitution = int(self.details['constitution'])
        avatar.intelligence = int(self.details['intelligence'])
        avatar.wisdom = int(self.details['wisdom'])
        avatar.charisma = int(self.details['charisma'])
        avatar.user = self.user
        avatar.current_block = self.block
        avatar.hp = avatar.max_hp
        avatar.xp = 0
        avatar.lv = 1
        avatar.items = dict(
            Coin=coin
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
            avatar = Avatar.get(self.user, self.block_id - 1)
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
            avatar = Avatar.get(self.user, self.block_id - 1)

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
            avatar = Avatar.get(self.user, self.block_id - 1)

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


class Sell(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'sell',
    }


class Buy(Move):
    __mapper_args__ = {
        'polymorphic_identity': 'buy',
    }


class User():
    def __init__(self, private_key):
        self.private_key = private_key
        self.public_key = str(seccure.passphrase_to_pubkey(
            self.private_key.encode('utf-8')
        ))
        self.address = h(self.public_key.encode('utf-8')).hexdigest()[:30]

    def sign(self, move):
        if move.name is None:
            raise InvalidNameError
        move.user = self.address
        serialized = move.serialize(include_signature=False)
        move.signature = '{signature} {public_key}'.format(
            signature=seccure.sign(
                serialized,
                self.private_key.encode('utf-8')
            ).decode('utf-8'),
            public_key=self.public_key,
        )
        move.id = move.hash

    @property
    def moves(self):
        return Move.query.filter_by(user=self.address).filter(
            Move.block != None # noqa
        ).order_by(Move.created_at.desc())

    def move(self, new_move, tax=0, commit=True):
        new_move.user = self.address
        new_move.tax = tax
        new_move.created_at = datetime.datetime.now()
        self.sign(new_move)

        if new_move.valid:
            if commit:
                db.session.add(new_move)
                db.session.commit()
        else:
            raise InvalidMoveError

        return new_move

    def hack_and_slash(self, spot=''):
        return self.move(HackAndSlash(details={'spot': spot}))

    def sleep(self, spot=''):
        return self.move(Sleep())

    def send(self, item_name, amount, receiver):
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

    def create_block(self, moves, commit=True):
        for move in moves:
            if not move.valid:
                raise InvalidMoveError(move)
        # TODO: Need to add block size limit
        block = Block()
        block.root_hash = h(
            ''.join(sorted((m.id for m in moves))).encode('utf-8')
        ).hexdigest()
        block.creator = self.address
        block.created_at = datetime.datetime.now()

        prev_block = Block.query.order_by(Block.id.desc()).first()
        if prev_block:
            block.id = prev_block.id + 1
            block.prev_hash = prev_block.hash
            block.difficulty = prev_block.difficulty
            if (block.created_at - prev_block.created_at <=
               datetime.timedelta(0, 5)):
                block.difficulty = block.difficulty + 1
            elif (block.created_at - prev_block.created_at >=
                  datetime.timedelta(0, 15)):
                block.difficulty = block.difficulty - 1
        else:
            #: Genesis block
            block.id = 1
            block.prev_hash = None
            block.difficulty = 0
        block.suffix = hashcash._mint(
            block.serialize().decode('utf-8'),
            bits=block.difficulty
        )
        block.hash = h(
            (block.serialize().decode('utf-8') + block.suffix).encode('utf-8')
        ).hexdigest()

        for move in moves:
            move.block = block

        if commit:
            db.session.add(block)
            db.session.commit()

        return block

    def avatar(self, block_id=None):
        if not block_id:
            block = Block.query.order_by(Block.id.desc()).first()
            if block:
                block_id = block.id
            else:
                block_id = 0
        return Avatar.get(self.address, block_id)


class Avatar():
    @classmethod
    @cache.memoize()
    def get(cls, user_addr, block_id):
        create_move = Move.query.filter_by(user=user_addr).filter(
            Move.block_id <= block_id
        ).order_by(
            Move.block_id.desc()
        ).filter(
            Move.name.like('create_%')
        ).first()
        if not create_move or block_id < create_move.block_id:
            return None
        moves = Move.query.filter(
            or_(Move.user == user_addr, Move.id.in_(
                    db.session.query(MoveDetail.move_id).filter_by(
                        key='receiver', value=user_addr)))
        ).filter(
            Move.block_id >= create_move.block_id,
            Move.block_id <= block_id
        )
        avatar, result = create_move.execute(None)
        avatar.items['Coin'] += Block.query.filter_by(
            creator=user_addr
        ).filter(Block.id <= block_id).count() * 8

        for move in moves:
            if move.user == user_addr:
                avatar, result = move.execute(avatar)
            if (type(move) == Send and
               move.details['receiver'] == user_addr):
                avatar, result = move.receive(avatar)

        return avatar

    def modifier(self, status):
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
        elif status == 18:
            return 3
        return 0

    def get_item(self, item):
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


class Novice(Avatar):
    __mapper_args__ = {
        'polymorphic_identity': 'novice',
    }

    @property
    def damage(self):
        return '1d6'

    @property
    def max_hp(self):
        return self.constitution + 6
