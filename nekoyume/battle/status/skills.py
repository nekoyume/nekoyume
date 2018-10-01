from dataclasses import dataclass

from .base import Status


@dataclass
class Attack(Status):
    type: str = 'attack'
    id_: str = ''
    value: int = 0
    target_id: str = ''
    target_hp: int = 0
    target_remain: int = 0


@dataclass
class Casting(Status):
    type: str = 'casting'
    id_: str = ''
    tick_remain: int = 0


@dataclass
class Delaying(Status):
    type: str = 'delaying'
    id_: str = ''
    tick_remain: int = 0


@dataclass
class Taunt(Status):
    type: str = 'taunt'
    id_: str = ''


@dataclass
class Heal(Status):
    type: str = 'heal'
    id_: str = ''
    value: int = 0
    target_id: str = ''
    target_hp: int = 0
    target_remain: int = 0
