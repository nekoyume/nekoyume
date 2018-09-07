#import time

from characters import Factory
from components.stats import Stats
from enums import CharacterType
from logger import Logger
from rand import Random


class Simulator:
    def __init__(self, seed):
        self.time = 0
        self.characters = []
        self.logger = Logger()
        self.random = Random(seed)

    def simulate(self):
        # todo: sorting by dex
        # self.random.shuffle(self.characters)
        while True:
            self.characters = sorted(self.characters, 
                key=lambda c: c.get_component(Stats).calc_atk_spd(), 
                reverse=True)
            #time.sleep(1)
            self.log('time .. ' + str(self.time))
            for character in self.characters:
                character.tick(self)
            self.time = self.time + 1
            if self.time >= 100:
                self.log('stop.')
                break
            is_win = True
            is_lose = True
            for character in self.characters:
                if character.type_ == CharacterType.MONSTER:
                    stats = character.get_component(Stats)
                    if stats != None and not stats.is_dead():
                        is_win = False
                if character.type_ == CharacterType.PLAYER:
                    stats = character.get_component(Stats)
                    if stats != None and not stats.is_dead():
                        is_lose = False
            if is_win:
                self.log('win!')
                break
            if is_lose:
                self.log('lose..')
                break
        self.log_result()

    def log(self, txt):
        self.logger.log(txt)

    def log_result(self):
        self.characters = sorted(self.characters, key=lambda c: c.type_)
        for character in self.characters:
            stats = character.get_component(Stats)
            if not stats.is_dead():
                self.log(character.name + ' is alive.. hp ' + str(stats.hp))
            else:
                self.log(character.name + ' is dead.. hp ' + str(stats.hp))


class NormalBattle(Simulator):
    def __init__(self, seed):
        super().__init__(seed)
        
        self.characters.append(Factory.create_player('dummy_swordman', 1, 'swordman', ['taunt', 'attack'], ['sword']))
        self.characters.append(Factory.create_player('dummy_mage', 1, 'mage', ['firewall', 'attack'], ['wand']))
        self.characters.append(Factory.create_player('dummy_acolyte', 1, 'acolyte', ['heal', 'attack'], ['bow']))
        self.characters.append(Factory.create_player('dummy_archer', 1, 'archer', ['attack'], ['bow']))
        self.characters.append(Factory.create_monster('slime'))
        self.characters.append(Factory.create_monster('slime'))
        self.characters.append(Factory.create_monster('slime'))
        self.characters.append(Factory.create_monster('slime'))
