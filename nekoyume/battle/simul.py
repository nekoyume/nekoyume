import random

from nekoyume.battle import WeightedList
from nekoyume.battle.characters import Factory
from nekoyume.battle.components.bag import Bag
from nekoyume.battle.components.stats import Stats
from nekoyume.battle.enums import CharacterType
from nekoyume.battle.items import Item
from nekoyume.battle.items.weapons import Weapon
from nekoyume.battle.logger import Logger
from nekoyume.battle.tables import Tables


class Simulator:
    def __init__(self, random: random.Random):
        self.time = 0
        self.characters = []
        self.logger = Logger()
        self.random = random
        self.result = ''  # win, lose, finish

    def simulate(self):
        while True:
            self.characters = sorted(
                self.characters,
                key=lambda c: c.get_component(Stats).calc_atk_spd(),
                reverse=True)
            for character in self.characters:
                character.tick(self)
            self.time = self.time + 1
            if self.time >= 100:
                self.result = 'finish'
                break
            is_win = True
            is_lose = True
            for character in self.characters:
                if character.type_ == CharacterType.MONSTER:
                    stats = character.get_component(Stats)
                    if stats is not None and not stats.is_dead():
                        is_win = False
                if character.type_ == CharacterType.PLAYER:
                    stats = character.get_component(Stats)
                    if stats is not None and not stats.is_dead():
                        is_lose = False
            if is_win:
                self.result = 'win'
                drop_items = WeightedList()
                for drop_id in Tables.drop:
                    drop = Tables.drop[drop_id]
                    drop_items.add(drop.item_id, drop.weight)
                for character in self.characters:
                    if character.type_ == CharacterType.PLAYER:
                        bag = character.get_component(Bag)
                        drop_item = drop_items.select(self.random)
                        if drop_item:
                            item_data = Tables.items[drop_item]
                            item = Item.subclasses[item_data.cls](drop_item)
                            item.option = self.random.randint(1, 5)
                            bag.add(item)
                            self.logger.log_item(item.name)
                break
            if is_lose:
                self.result = 'lose'
                break


class DummyBattle(Simulator):
    def __init__(self, seed):
        super().__init__(seed)
        self.characters.append(Factory.create_player(
            'dummy_swordman', 'swordman', 1, ['taunt', 'attack'], 
            [Weapon('sword')]))
        self.characters.append(Factory.create_player(
            'dummy_mage', 'mage', 1, ['firewall', 'attack'], []))
        self.characters.append(Factory.create_player(
            'dummy_acolyte', 'acolyte', 1, ['heal', 'attack'], []))
        self.characters.append(Factory.create_player(
            'dummy_archer', 'archer', 1, ['attack'], []))
        self.characters.append(Factory.create_monster('slime'))
        self.characters.append(Factory.create_monster('slime'))
        self.characters.append(Factory.create_monster('slime'))
        self.characters.append(Factory.create_monster('slime'))
        self.characters.append(Factory.create_monster('griffin'))
