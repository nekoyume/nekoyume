import datetime
from hashlib import sha256 as h

from bencode import bencode
from flask_sqlalchemy import SQLAlchemy
import seccure
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection
import tablib

import hashcash


db = SQLAlchemy()


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

    @property
    def valid(self):
        return (self.hash ==
                h(
                    (self.serialize() + self.suffix.encode('utf-8'))
                ).hexdigest())

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

    def execute(self, avatar=None):
        if not avatar:
            avatar = Avatar.get(self.user, self.block_id - 1)
        monsters = tablib.Dataset().load(open('monsters.csv').read()).dict
        randoms = self.get_randoms()
        monster = monsters[randoms.pop() % len(monsters)]
        battle_status = []

        for key in ('hp', 'piercing', 'armor'):
            monster[key] = int(monster[key])

        while True:
            try:
                rolled = self.roll(randoms, '2d6')
                if rolled in (7, 8, 9, 10, 11, 12):
                    damage = self.roll(randoms, avatar.damage)
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
                return (avatar, dict(
                    type='hack_and_slash',
                    result='finish',
                    battle_status=battle_status,
                ))


class Sleep(Move):
    __mapper_args__ = {
        'polymorphic_identity':'sleep',
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
        'polymorphic_identity':'create_novice',
    }

    def execute(self, avatar=None):
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

        return (avatar, dict(
            type='create_novice',
            result='success',
        ))


class LevelUp(Move):
    __mapper_args__ = {
        'polymorphic_identity':'level_up',
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
        'polymorphic_identity':'say',
    }

    def execute(self, avatar=None):
        if not avatar:
            avatar = Avatar.get(self.user, self.block_id - 1)

        return avatar, dict(
            type='say',
            message=self.details['content'],
        )


class Sell(Move):
    __mapper_args__ = {
        'polymorphic_identity':'sell',
    }


class Buy(Move):
    __mapper_args__ = {
        'polymorphic_identity':'buy',
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

    @property
    def moves(self):
        return Move.query.filter_by(user=self.address).filter(
            Move.block != None
        ).order_by(Move.created_at.desc())

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

    def sleep(self, spot=''):
        return self.move(Sleep())

    def sell(self, item_code, price):
        return self.move(Sell(details={'item_code': item_code,
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

        if commit:
            db.session.add(block)
            db.session.commit()

        return block

    def avatar(self, block_id=None):
        if not block_id:
            block_id = Block.query.order_by(Block.id.desc()).first().id
        return Avatar.get(self.address, block_id)


class Avatar():
    @classmethod
    def get(cls, user_addr, block_id):
        create_move = Move.query.filter_by(user=user_addr).filter(
            Move.block_id <= block_id).order_by(Move.block_id.desc()
        ).filter(
            Move.name.like('create_%')
        ).first()
        if not create_move or block_id < create_move.block_id:
            return None
        moves = Move.query.filter_by(
            user=user_addr
        ).filter(
            Move.block_id >= create_move.block_id,
            Move.block_id <= block_id
        )
        avatar = create_move.execute(None)
        for move in moves:
            avatar, result = move.execute(avatar)
        return avatar

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
