import datetime
from hashlib import sha256 as h

from bencode import bencode
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import seccure
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection
import tablib

import hashcash


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)


class InvalidNameError(Exception):
    pass


class InvalidMoveError(Exception):
    pass


class OutOfRandomError(Exception):
    pass


class Block(db.Model):
    __tablename__ = 'block'
    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String, nullable=False, index=True)
    prev_hash = db.Column(db.String,
                          db.ForeignKey('block.hash'),
                          index=True)
    prev = db.relationship('Block', remote_side=[hash], uselist=False)
    creator = db.Column(db.String, nullable=False, index=True)
    root_hash = db.Column(db.String, nullable=False)
    suffix = db.Column(db.String, nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.now())

    def serialize(self, use_bencode=True, include_suffix=False):
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
        if use_bencode:
            if self.prev_hash is None:
               del serialized['prev_hash']
            serialized = bencode(serialized)
        return serialized


class Move(db.Model):
    __tablename__ = 'move'
    id = db.Column(db.String, primary_key=True)
    block_id = db.Column(db.Integer, db.ForeignKey('block.id'),
                         nullable=True, index=True)
    block = db.relationship('Block', uselist=False, backref='moves')
    user = db.Column(db.String, nullable=False, index=True)
    signature = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False, index=True)
    details = association_proxy('move_details', 'value',
        creator=lambda k, v: MoveDetail(key=k, value=v)
    )
    tax = db.Column(db.BigInteger, default=0, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.now())

    __mapper_args__ = {
        'polymorphic_identity':'move',
        'polymorphic_on':name,
    }

    def sign(self, private_key):
        if self.name is None:
            raise InvalidNameError
        user = User(private_key)
        self.user = user.address
        serialized = self.serialize(include_signature=False)
        self.signature = '{signature} {public_key}'.format(
            signature=seccure.sign(
                serialized,
                user.private_key.encode('utf-8')
            ).decode('utf-8'),
            public_key=user.public_key,
        )
        self.id = self.hash

    @property
    def valid(self):
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

    def serialize(self, use_bencode=True, include_signature=False):
        serialized = dict(
            user=self.user,
            name=self.name,
            details=dict(self.details),
            tax=self.tax,
            created_at=str(self.created_at),
        )
        if include_signature:
            serialized['signature'] = self.signature
        if use_bencode:
            serialized = bencode(serialized)
        return serialized

    @property
    def hash(self):
        return h(self.serialize(include_signature=True)).hexdigest()

    def get_randoms(self):
        if not (self.block and self.block.hash and self.id):
            return []
        result = [ord(a) ^ ord(b) for a,b in zip(self.block.hash, self.id)]
        result = result[int(self.block.difficulty / 4):]
        return result

    def roll(self, randoms, dice, sum_=True):
        result = []
        cnt, dice_type = (int(i) for i in dice.split('d'))
        for i in range(cnt):
            try:
                result.append(randoms.pop() % dice_type + 1)
            except IndexError:
                raise OutOfRandomError
        if sum_:
            return sum(result)
        else:
            return result


class HackAndSlash(Move):
    __mapper_args__ = {
        'polymorphic_identity':'hack_and_slash',
    }

    def execute(self):
        monsters = tablib.Dataset().load(open('monsters.csv').read()).dict
        randoms = self.get_randoms()
        monster = monsters[randoms.pop() % len(monsters)]
        avatar = Avatar.query.get(self.user)
        for key in ('hp', 'piercing', 'armor'):
            monster[key] = int(monster[key])

        while True:
            try:
                rolled = self.roll(randoms, '2d6')
                if rolled in (7, 8, 9, 10, 11, 12):
                    monster['hp'] = monster['hp'] - self.roll(randoms,
                                                              avatar.damage)
                    print(f'{monster["id"]}({monster["hp"]})가 맞았다.')
                elif rolled in (2, 3, 4, 5, 6, 7, 8, 9):
                    avatar.hp -= self.roll(randoms, monster['damage'])
                    print(f'{avatar.user}({avatar.hp})가 맞았다.')
                    if rolled <= 6:
                        avatar.xp += 1
                        print(f'{avatar.user}는 아까의 과오에서 깨달은 게 있다.')

                if monster['hp'] <= 0:
                    print(f'{monster["id"]}({monster["hp"]})가 죽었다.')
                    return True
                if avatar.hp <= 0:
                    print(f'{avatar.user}({avatar.hp})가 죽었다.')
                    return True
            except OutOfRandomError:
                return True


class Sell(Move):
    __mapper_args__ = {
        'polymorphic_identity':'sell',
    }


class Buy(Move):
    __mapper_args__ = {
        'polymorphic_identity':'buy',
    }


class CreateNovice(Move):
    __mapper_args__ = {
        'polymorphic_identity':'create_novice',
    }

    def execute(self):
        origin = Avatar.query.filter_by(user=self.user).first()
        if origin:
            db.session.delete(origin)
            db.session.commit()

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

        db.session.add(avatar)
        db.session.commit()
        return True


class LevelUp(Move):
    __mapper_args__ = {
        'polymorphic_identity':'level_up',
    }

class Say(Move):
    __mapper_args__ = {
        'polymorphic_identity':'say',
    }


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


class User():
    def __init__(self, private_key):
        self.private_key = private_key
        self.public_key = str(seccure.passphrase_to_pubkey(
            self.private_key.encode('utf-8')
        ))
        self.address = h(self.public_key.encode('utf-8')).hexdigest()[:30]

    def move(self, new_move, tax=0, commit=True):
        new_move.user=self.address
        new_move.tax=tax
        new_move.created_at=datetime.datetime.now()
        new_move.sign(self.private_key)

        if new_move.valid:
            if commit:
                db.session.add(new_move)
                db.session.commit()
        else:
            raise InvalidMoveError

        return new_move

    def hack_and_slash(self, spot=''):
        return self.move(HackAndSlash(details={'spot': spot}))

    def sell(self, item_code, price):
        return self.move(Sell(details={'item_code': item_code,
                                       'price': price}))

    def buy(self, move_id):
        return self.move(Buy(details={'move_id': move_id}))

    def create_novice(self, details):
        return self.move(CreateNovice(details=details))

    def level_up(self, new_status, new_advanced_move):
        return self.move(LevelUp(details={
            'new_status': new_status,
            'new_advanced_move': new_advanced_move,
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
               datetime.timedelta(0, 15)):
                block.difficulty = block.difficulty + 1
            elif (block.created_at - prev_block.created_at >=
               datetime.timedelta(30)):
                block.difficulty = block.difficulty - 1
        else: # genesis block
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
            move.execute()

        if commit:
            db.session.add(block)
            db.session.commit()

        return block


class Avatar(db.Model):
    user = db.Column(db.String, nullable=False, primary_key=True)
    job = db.Column(db.String, nullable=False, default='avatar')

    current_block_id = db.Column(db.Integer, db.ForeignKey('block.id'),
                                 nullable=True, index=True)
    current_block = db.relationship('Block', uselist=False, backref='avatars')

    level = db.Column(db.Integer, nullable=False, default=1)
    hp = db.Column(db.Integer, nullable=False, default=1)
    xp = db.Column(db.Integer, nullable=False, default=0)

    strength = db.Column(db.Integer, nullable=False, default=0)
    weak = db.Column(db.Boolean, nullable=False, default=False)

    dexterity = db.Column(db.Integer, nullable=False, default=0)
    shaky = db.Column(db.Boolean, nullable=False, default=False)

    constitution = db.Column(db.Integer, nullable=False, default=0)
    sick = db.Column(db.Boolean, nullable=False, default=False)

    intelligence = db.Column(db.Integer, nullable=False, default=0)
    stunned = db.Column(db.Boolean, nullable=False, default=False)

    wisdom = db.Column(db.Integer, nullable=False, default=0)
    confused = db.Column(db.Boolean, nullable=False, default=False)

    charisma = db.Column(db.Integer, nullable=False, default=0)
    scarred = db.Column(db.Boolean, nullable=False, default=False)

    __mapper_args__ = {
        'polymorphic_identity':'avatar',
        'polymorphic_on':job,
    }

    @property
    def damage(self):
        raise NotImplementedError

    @property
    def max_hp(self):
        raise NotImplementedError


class Novice(Avatar):
    __mapper_args__ = {
        'polymorphic_identity':'novice',
    }

    @property
    def damage(self):
        return '1d6'

    @property
    def max_hp(self):
        return self.constitution + 6
