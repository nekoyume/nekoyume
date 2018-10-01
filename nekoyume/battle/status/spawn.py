from dataclasses import dataclass

from ..characters import Character
from ..components.bag import Bag
from ..components.stats import Stats
from .base import Status


@dataclass
class Spawn(Status):
    type: str = 'spawn'
    id_: str = ''
    class_: str = '' # noqa
    character_type: int = 0
    name: str = ''
    level: int = 0
    hp: int = 0
    hp_max: int = 0
    armor: str = ''
    head: str = ''
    weapon: str = ''

    @classmethod
    def from_character(cls, character: Character):
        bag = character.get_component(Bag)
        stats = character.get_component(Stats)
        return Spawn(
            id_=character.id_,
            class_=character.class_,
            character_type=character.type_,
            name=character.name,
            level=getattr(stats, 'level', 0),
            hp=stats.hp,
            hp_max=stats.calc_hp_max(),
            armor=bag.armor_name,
            head=bag.head_name,
            weapon=bag.weapon_name,
        )
