from dataclasses import dataclass

from .base import Status


@dataclass
class Dead(Status):
    type: str = 'dead'
    id_: str = ''


@dataclass
class GetExp(Status):
    type: str = 'get_exp'
    exp: int = 0
