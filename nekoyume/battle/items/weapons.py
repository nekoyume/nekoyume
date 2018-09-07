from enums import AttackType
from items.items import Item, Equipment


class Weapon(Equipment):
    def __init__(self, name):
        super().__init__(name)
        self.atk_type = AttackType.MELEE

    def get_atk(self):
        return self.param_0


class RangedWeapon(Weapon):
    def __init__(self, name):
        super().__init__(name)
        self.atk_type = AttackType.RANGED
