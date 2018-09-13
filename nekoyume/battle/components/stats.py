import math

from nekoyume.battle.components import Component
from nekoyume.battle.enums import CharacterType
from nekoyume.tables import Tables


class Stats(Component):
    def __init__(self):
        self.is_damaged = False

    def get_target_type(self):
        player = self.owner.type_ == CharacterType.PLAYER
        return CharacterType.MONSTER if player else CharacterType.PLAYER

    def calc_melee_atk(self):
        return self.data.strength + math.floor(self.data.dexterity * 0.2)

    def calc_ranged_atk(self):
        return self.data.dexterity + math.floor(self.data.strength * 0.2)

    def calc_magic_atk(self):
        return self.data.intelligence

    def calc_atk_spd(self):
        return self.data.dexterity

    def calc_cooltime(self, cooltime):
        return cooltime

    def calc_defense(self):
        return self.data.get('defense', 0)

    def calc_hp_max(self):
        return self.data.constitution * 10

    def damaged(self, damage):
        damage -= self.calc_defense()
        self.hp = max(self.hp - damage, 0)
        self.is_damaged = True
        return damage

    def check_damaged(self):
        damaged = self.is_damaged
        self.is_damaged = False
        return damaged

    def heal(self, amount):
        self.hp = min(self.hp + amount, self.calc_hp_max())

    def is_dead(self):
        return self.hp <= 0


class PlayerStats(Stats):
    def __init__(self, class_, level, hp, exp):
        self.data = Tables.stats.get(class_)
        super().__init__()
        self.level = level
        self.hp = hp
        self.exp = exp
        self.exp_max = Tables.get_exp_max(level)

    def get_exp(self, exp):
        self.exp += exp
        while self.exp >= self.exp_max:
            self.exp -= self.exp_max
            self.level += 1
        self.exp_max = Tables.get_exp_max(self.level)


class MonsterStats(Stats):
    def __init__(self, name):
        self.data = Tables.monsters.get(name)
        super().__init__()
        self.name = name
        self.hp = self.calc_hp_max()
