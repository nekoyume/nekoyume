from ..battle.enums import ItemType
from .base import Equipment


class Armor(Equipment):
    def __init__(self, name):
        super().__init__(name)
        self.type_ = ItemType.ARMOR
