from nekoyume.battle.enums import ItemType
from nekoyume.items.base import Equipment


class Head(Equipment):
    def __init__(self, name):
        super().__init__(name)
        self.type_ = ItemType.HEAD
