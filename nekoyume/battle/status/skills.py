from dataclasses import dataclass

from .base import Status


@dataclass
class Skill(Status):
    type: str = ''
    name: str = ''


@dataclass
class Attack(Skill):
    type: str = 'attack'
    id_: str = ''
    value: int = 0
    target_id: str = ''
    target_hp: int = 0
    target_remain: int = 0


@dataclass
class Casting(Skill):
    type: str = 'casting'
    id_: str = ''
    tick_remain: int = 0


@dataclass
class Delaying(Skill):
    type: str = 'delaying'
    id_: str = ''
    tick_remain: int = 0


@dataclass
class Taunt(Skill):
    type: str = 'taunt'
    id_: str = ''


@dataclass
class Heal(Skill):
    type: str = 'heal'
    id_: str = ''
    value: int = 0
    target_id: str = ''
    target_hp: int = 0
    target_remain: int = 0
