from dataclasses import dataclass

from .base import Status


@dataclass
class Zone(Status):
    type: str = 'zone'
    id_: str = ''
