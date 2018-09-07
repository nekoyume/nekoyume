import math

from components.component import Component
from enums import CharacterType, AttackType

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
        self.hp_max = self.constitution * 10
        if hp_recovery:
            self.hp = self.hp_max
        self.is_damaged = False
        self.skill = None

    def get_target_type(self):
        return CharacterType.MONSTER if self.owner.type_ == CharacterType.PLAYER else CharacterType.PLAYER

    def calc_melee_atk(self):
        return self.strength + math.floor(self.dexterity * 0.2)

    def calc_ranged_atk(self):
        return self.dexterity + math.floor(self.strength * 0.2)

    def calc_magic_atk(self):
        return self.intelligence

    def calc_atk_spd(self):
        return self.dexterity

    def calc_cooltime(self, cooltime):
        return cooltime

    def current_hp(self):
        return self.hp

    def damaged(self, damage):
        damage -= self.defense
        self.hp = max(self.hp - damage, 0)
        self.is_damaged = True
        return damage

    def check_damaged(self):
        ret = self.is_damaged
        self.is_damaged = False
        return ret

    def heal(self, amount):
        self.hp = min(self.hp + amount, self.hp_max)

    def is_dead(self):
        return self.hp <= 0
