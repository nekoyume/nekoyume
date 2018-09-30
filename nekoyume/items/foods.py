from ..battle.enums import ItemType
from .base import UseItem


class Food(UseItem):
    def __init__(self, name):
        super().__init__(name)
        self.type_ = ItemType.FOOD
