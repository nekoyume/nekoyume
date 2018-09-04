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
    def __init__(self, level, stats):
        self.level = level
        self.strength = int(stats['strength'])
        self.dexterity = int(stats['dexterity'])
        self.intelligence = int(stats['intelligence'])
        self.constitution = int(stats['constitution'])
        self.wisdom = int(stats['wisdom'])
        self.luck = 0
        self.hp = self.hp_max = self.constitution * 10

    def calc_melee_atk(self):
        return self.strength

    def calc_range_atk(self):
        return self.dexterity

    def calc_magic_atk(self):
        return self.intelligence

    def clac_max_hp(self):
        return self.constitution

    def current_hp(self):
        return self.hp

    def calc_atk_cooltime(self):
        return 5

    def damaged(self, damage):
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
