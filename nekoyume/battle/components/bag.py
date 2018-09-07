from components.component import Component
from items.items import Item
from items.weapons import Weapon
from tables import Tables


class Bag(Component):
    def __init__(self, itemnames=[]):
        self.items = {}
        for itemname in itemnames:
            data = Tables.items[itemname]
            itemcls = data['cls']
            self.add(Item.subclasses[itemcls](itemname))

    def add(self, item):
        # todo
        self.items[item.name] = item

    def get_weapon(self):
        return None
