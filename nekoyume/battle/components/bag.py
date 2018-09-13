from nekoyume.battle.components import Component
from nekoyume.battle.enums import ItemType


class Bag(Component):
    def __init__(self, items=None, weapon_index=0, armor_index=0):
        if items is None:
            items = []
        self.items = items

    def get(self, index):
        try:
            return self.items[index]
        except IndexError:
            return None

    def find(self, name):
        for item in self.items:
            if item.name == name:
                return item
        return None

    def add(self, item):
        if item.type_ == ItemType.ITEM:
            my_item = self.find(item.name)
            if my_item is None:
                self.items.append(item)
            else:
                my_item.amount += item.amount
        else:
            self.items.append(item)

    def get_equipped(self, type_):
        for item in self.items:
            if item.type_ == type_ and item.is_equipped:
                return item

    def equip(self, item_index):
        item = self.get(item_index)
        if item:
            equipped = self.get_equipped(item.type_)
            if equipped:
                equipped.unequip()
            item.equip()
