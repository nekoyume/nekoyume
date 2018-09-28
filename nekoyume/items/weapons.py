from ..battle.enums import AttackType, ItemType
from .base import Equipment


class Weapon(Equipment):
    def __init__(self, name):
        super().__init__(name)
        self.type_ = ItemType.WEAPON
        self.atk_type = AttackType.MELEE

    def get_atk(self):
        return self.data.param_0


class RangedWeapon(Weapon):
    def __init__(self, name):
        super().__init__(name)
        self.atk_type = AttackType.RANGED
