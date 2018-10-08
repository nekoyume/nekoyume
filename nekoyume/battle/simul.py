import random

from ..items import Item
from ..items.weapons import Weapon
from ..tables import Tables
from .characters import Factory
from .components.bag import Bag
from .components.stats import Stats
from .enums import CharacterType
from .logger import Logger
from .status.item import GetItem
from .status.spawn import Spawn
from .status.zone import Zone


class Simulator:
    def __init__(self, random: random.Random, zone: str):
        self.time = 0
        self.characters = []
        self.logger = Logger()
        self.zone = zone
        self.random = random
        self.result = ''  # win, lose, finish

    def simulate(self):
        self.logger.log(Zone(id_=self.zone))

        for character in self.characters:
            self.logger.log(Spawn.from_character(character))

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
                    if not stats.is_dead():
                        is_win = False
                if character.type_ == CharacterType.PLAYER:
                    stats = character.get_component(Stats)
                    if not stats.is_dead():
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
                            # TODO item option
                            item.option = self.random.randint(1, 5)
                            bag.add(item)
                            self.logger.log(GetItem(
                                id_=character.id_,
                                item=item.name
                            ))
                break
            if is_lose:
                self.result = 'lose'
                break


class DummyBattle(Simulator):
    def __init__(self, seed):
        super().__init__(seed, 'zone_0')
        factory = Factory()
        self.characters.append(factory.create_player(
            'dummy_swordman', 'swordman', 5, [Weapon('sword_1')]))
        self.characters.append(factory.create_player(
            'dummy_mage', 'mage', 5, []))
        self.characters.append(factory.create_player(
            'dummy_mage', 'acolyte', 5, []))
        self.characters.append(factory.create_monster('slime'))
        self.characters.append(factory.create_monster('slime'))
        # self.characters.append(factory.create_monster('griffin'))
