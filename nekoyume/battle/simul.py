#import time

from players import Warrior, Mage, Monk, DummyPlayer
from monsters import Griffin, Slime
from components import Stats
from enums import CharacterType, ClassType
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
        self.random.shuffle(self.characters)
        while True:
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
                if character.get_type() == CharacterType.MONSTER:
                    stats = character.get_component(Stats)
                    if stats != None and not stats.is_dead():
                        is_win = False
                if character.get_type() == CharacterType.PLAYER:
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
        self.characters = sorted(self.characters, key=lambda c: c.group)
        for character in self.characters:
            stats = character.get_component(Stats)
            if not stats.is_dead():
                self.log(character.name + ' is alive.. hp ' + str(stats.hp))
            else:
                self.log(character.name + ' is dead.. hp ' + str(stats.hp))


class NormalBattle(Simulator):
    def __init__(self, seed):
        super().__init__(seed)
        self.characters.append(DummyPlayer('swordman', ClassType.SWORDMAN, [('Attack', 2)]))
        #self.characters.append(Warrior())
        self.characters.append(Mage())
        self.characters.append(Monk())
        self.characters.append(Slime())
        self.characters.append(Griffin())
        
