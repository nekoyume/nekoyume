class Item():
    ticker_name = 'XXX'


class Combined():
    recipe = {}
    dice = '1d1'


class Weapon(Item):
    @classmethod
    def attack_modifier(cls, avatar, monster):
        raise NotImplementedError


class Armor(Item):
    @classmethod
    def armor_modifier(cls, avatar, monster):
        raise NotImplementedError


class Food(Item):
    def execute(self, avatar):
        raise NotImplementedError


class HPFood(Food):
    def __init__(self, amount):
        self.heal_amount = amount

    def execute(self, avatar):
        avatar.hp = min(avatar.max_hp, avatar.hp + self.heal_amount)
        return avatar, {
            'type': 'item_use',
            'item': self.ticker_name,
            'status_change': f'HP +{self.heal_amount}'
        }


class HPMaxFood(Food):
    def execute(self, avatar):
        avatar.hp = avatar.max_hp
        return avatar, {
            'type': 'item_use',
            'item': self.ticker_name,
            'status_change': 'HP MAX'
        }


# Tier 1 Food (10HP)
class MeatPlatter(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'MPLT'
    recipe = {'MEAT', 'MEAT', 'MEAT'}


class Oyakodon(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'OYKD'
    recipe = {'RICE', 'EGGS', 'CHKN'}


class Carbonara(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'CBNR'
    recipe = {'WHET', 'EGGS', 'MEAT'}


class Steakdon(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'STKD'
    recipe = {'RICE', 'RKST', 'MEAT'}


class ChickenRice(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'CHKR'
    recipe = {'RICE', 'RKST', 'CHKN'}


class Steak(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'STEK'
    recipe = {'MEAT', 'RKST', 'OLIV'}


class FriedChicken(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'FCHK'
    recipe = {'CHKN', 'RKST', 'OLIV'}


class FriedRice(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'FRRC'
    recipe = {'RKST', 'RICE', "OLIV"}


class Bread(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'BRED'
    recipe = {'WHET', 'EGGS', 'OLIV'}


class FriedEgg(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'FREG'
    recipe = {'EGGS', 'OLIV', 'RKST'}


class EggTart(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'FREG'
    recipe = {'EGGS', 'OLIV', 'RKST'}


class PoorMansPizza(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 10)

    ticker_name = 'PMPZ'
    recipe = {'MEAT', 'WHET', 'OLIV'}


# Tier 2 (20HP)
class ChickenFriedRice(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 20)

    ticker_name = 'CFRC'
    recipe = {'FRRC', 'CHKN', 'CHKN'}


class EggFriedRice(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 20)

    ticker_name = 'EFRC'
    recipe = {'FRRC', 'EGGS', 'EGGS'}


class MeatFriedRice(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 20)

    ticker_name = 'MFRC'
    recipe = {'FRRC', 'MEAT', 'MEAT'}


class SteakSandwich(Combined, HPFood):
    def __init__(self):
        HPFood.__init__(self, 20)

    ticker_name = 'SKSW'
    recipe = {'BRED', 'STEK'}


# HP Max Foods
class SteakCarbonara(Combined, HPMaxFood):
    ticker_name = 'STCB'
    recipe = {'STEK', 'WHET', 'EGGS'}


class MasterFriedRice(Combined, HPMaxFood):
    ticker_name = 'MAFR'
    recipe = {'CFRC', 'EFRC', 'MFRC'}


class MeatLoversBurger(Combined, HPMaxFood):
    ticker_name = 'MLBG'
    recipe = {'FCHK', 'FCHK', 'MPLT'}


class LongSword(Weapon):
    ticker_name = 'LSWD'

    @classmethod
    def attack_modifier(cls, avatar, monster):
        return 1


class FlameSword(Combined, Weapon):
    ticker_name = 'FSWD'
    recipe = {'LSWD', 'FLNT', 'OLIV'}

    @classmethod
    def attack_modifier(cls, avatar, monster):
        if 'Wooden' in monster['special']:
            return 2
        else:
            return 1


class FlameSword1(Combined, Weapon):
    ticker_name = 'FSW1'
    recipe = {'FSWD', 'FSWD', 'FSWD'}

    @classmethod
    def attack_modifier(cls, avatar, monster):
        if 'Wooden' in monster['special']:
            return 4
        else:
            return 2


class FlameSword2(Combined, Weapon):
    ticker_name = 'FSW2'
    recipe = {'FSW1', 'FSW1', 'FSW1'}

    @classmethod
    def attack_modifier(cls, avatar, monster):
        if 'Wooden' in monster['special']:
            return 6
        else:
            return 3


class FlameSword3(Combined, Weapon):
    ticker_name = 'FSW3'
    recipe = {'FSW2', 'FSW2', 'FSW2'}

    @classmethod
    def attack_modifier(cls, avatar, monster):
        if 'Wooden' in monster['special']:
            return 8
        else:
            return 4


class LeatherMail(Armor):
    ticker_name = 'LMIL'

    @classmethod
    def armor_modifier(cls, avatar, monster):
        return 1


def get_related_items(cls) -> set:
    subclasses = set()
    pool = [cls]
    while pool:
        parent = pool.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                if child.ticker_name != 'XXX':
                    subclasses.add(child)
                pool.append(child)
    return subclasses
