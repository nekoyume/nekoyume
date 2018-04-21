class Item():
    ticker_name = 'XXX'
    pass


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


class HP10Food(Food):
    def execute(self, avatar):
        avatar.hp = min(avatar.max_hp, avatar.hp + 10)
        return avatar, {
            'type': 'item_use',
            'item': self.ticker_name,
            'status_change': 'HP +10'
        }


class HPMaxFood(Food):
    def execute(self, avatar):
        avatar.hp = avatar.max_hp
        return avatar, {
            'type': 'item_use',
            'item': self.ticker_name,
            'status_change': 'HP MAX'
        }


class MeatPlatter(Combined, HP10Food):
    ticker_name = 'MPLT'
    recipe = {'MEAT', 'MEAT', 'MEAT'}


class Oyakodong(Combined, HP10Food):
    ticker_name = 'OYKD'
    recipe = {'RICE', 'EGGS', 'CHKN'}


class Carbonara(Combined, HP10Food):
    ticker_name = 'CBNR'
    recipe = {'WHET', 'EGGS', 'MEAT'}


class Steakdong(Combined, HP10Food):
    ticker_name = 'STKD'
    recipe = {'RICE', 'RKST', 'MEAT'}


class ChickenRice(Combined, HP10Food):
    ticker_name = 'CHKR'
    recipe = {'RICE', 'RKST', 'CHKN'}


class Steak(Combined, HP10Food):
    ticker_name = 'STEK'
    recipe = {'MEAT', 'RKST', 'OLIV'}


class SteakCarbonara(Combined, HPMaxFood):
    ticker_name = 'STCB'
    recipe = {'STEK', 'WHET', 'EGGS'}


class FriedChicken(Combined, HP10Food):
    ticker_name = 'FCHK'
    recipe = {'CHKN', 'RKST', 'OLIV'}


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
