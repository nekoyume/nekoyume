import math
from utils import itersubclasses


class ComponentContainer:
    def __init__(self):
        self.components = []

    def add_component(self, comp):
        comp.owner = self
        self.components.append(comp)
        return comp

    def remove_component(self, comp):
        comp.owner = None
        self.components.remove(comp)
    
    def get_component(self, cls):
        for comp in self.components:
            if comp.__class__ == cls:
                return comp

    def get_components(self, cls):
        ret = []
        subclasses = itersubclasses(cls)
        for subcls in subclasses:
            for comp in self.components:
                    if comp.__class__ == subcls:
                        ret.append(comp)
        return ret


class Component:
    def __init__(self):
        self.owner = None
    
    def send_message(self, msg):
        for comp in self.owner.components:
            if not comp == self:
                comp.on_message(msg)

    def on_message(self, msg):
        pass


class Stats(Component):
    def __init__(self, level, data):
        self.set_data(level, data)

    def set_data(self, level, data, hp_recovery=True):
        self.level = level
        self.strength = int(data['strength'])
        self.dexterity = int(data['dexterity'])
        self.intelligence = int(data['intelligence'])
        self.constitution = int(data['constitution'])
        self.luck = int(data['luck'])
        self.defense = int(data['defense']) if 'defense' in data else 0
        self.hp_max = self.constitution
        if hp_recovery:
            self.hp = self.hp_max

    def calc_melee_atk(self):
        return self.strength + math.floor(self.dexterity * 0.2)

    def calc_ranged_atk(self):
        return self.dexterity + math.floor(self.strength * 0.2)

    def calc_magic_atk(self):
        return self.intelligence

    def calc_atk_cooltime(self):
        return 5

    def current_hp(self):
        return self.hp

    def damaged(self, damage):
        damage -= self.defense
        self.hp = max(self.hp - damage, 0)

    def heal(self, amount):
        self.hp = min(self.hp + amount, self.hp_max)

    def is_dead(self):
        return self.hp <= 0


class Aggro(Component):
    def __init__(self):
        self.targets = {}
    
    def tick(self, simulator):
        self.targets
