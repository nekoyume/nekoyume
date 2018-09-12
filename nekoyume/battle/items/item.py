from nekoyume.battle.tables import Tables
from nekoyume.battle.enums import ItemType


class Item:
    subclasses = {}

    def __init_subclass__(cls):
        super().__init_subclass__()
        Item.subclasses[cls.__name__] = cls

    def __init__(self, name, amount=1):
        self.type_ = ItemType.ITEM
        self.name = name
        self.amount = amount
        self.data = Tables.items[name]


class Equipment(Item):
    def __init__(self, name):
        super().__init__(name)
        self.is_equipped = False

    def equip(self):
        self.is_equipped = True

    def unequip(self):
        self.is_equipped = False


class Armor(Item):
    def __init__(self, name):
        super().__init__(name)
        self.type_ = ItemType.ARMOR
