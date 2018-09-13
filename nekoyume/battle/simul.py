import random

from nekoyume.battle.characters import Factory
from nekoyume.battle.components.bag import Bag
from nekoyume.battle.components.stats import Stats
from nekoyume.battle.enums import CharacterType
from nekoyume.items import Item
from nekoyume.items.weapons import Weapon
from nekoyume.battle.logger import Logger
from nekoyume.tables import Tables


class Simulator:
    def __init__(self, random: random.Random, zone):
        self.time = 0
        self.characters = []
        self.logger = Logger()
        self.zone = zone
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
                drop_items = Tables.get_item_drop_list(self.zone)
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
            [Weapon('sword_1')]))
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
