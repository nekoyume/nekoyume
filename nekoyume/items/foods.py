from nekoyume.battle.enums import ItemType
from nekoyume.items.base import UseItem


class Food(UseItem):
    def __init__(self, name):
        super().__init__(name)
        self.type_ = ItemType.FOOD
