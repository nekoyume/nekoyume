import math

from components.component import Component
from components.aggro import Aggro
from components.bag import Bag
from components.stats import Stats
from enums import CharacterType, AttackType
from rand import WeightedList
from behaviors import BehaviorTreeStatus
from tables import Tables


class Skill(Component):
    subclasses = {}
    def __init_subclass__(cls):
        super().__init_subclass__()
        Skill.subclasses[cls.__name__] = cls

    def __init__(self, name):
        self.name = name
        data = Tables.skills[name]
        self.cast_time = int(data['cast_time'])
        self.cooltime = int(data['cooltime'])
        self.target_count = int(data['target_count'])
        self.power = float(data['power']) * 0.01
        self.nexttime = self.cooltime
        self.is_casting = False
        self.cast_remains = 0

    def tick(self, simulator):
        pass

    # todo: is_dead check to filter
    def find_targets(self, targets, filter_type):
        if self.target_count <= 0:
            return []
        weightedlist = WeightedList()
        for target in targets:
            stats = target.get_component(Stats)
            aggro = target.get_component(Aggro)
            if filter_type == target.type_\
               and not stats.is_dead():
                weightedlist.add(target, aggro.value)
        if len(weightedlist) == 0:
            return []
        find = []
        while len(find) < self.target_count:
            find.append(weightedlist.pop())
            if len(weightedlist) == 0:
                break
        return find


# weapon based attack
class Attack(Skill):
    def tick(self, simulator):
        if self.nexttime > simulator.time:
            return BehaviorTreeStatus.FAILURE
        my_stats = self.owner.get_component(Stats)
        if not my_stats:
            return BehaviorTreeStatus.FAILURE
        # calc atk
        my_bag = self.owner.get_component(Bag)
        weapon = my_bag.get_weapon()
        atk = 0
        if weapon:
            atk = weapon.get_atk()
            if weapon.atk_type == AttackType.MELEE:
                atk += my_stats.calc_melee_atk()
            elif weapon.atk_type == AttackType.RANGED:
                atk += my_stats.calc_ranged_atk()
            elif weapon.atk_type == AttackType.MAGIC:
                atk += my_stats.calc_magic_atk()
        else:
            atk += my_stats.calc_melee_atk()
        atk = math.floor(atk * self.power)
        # find target
        target_type = my_stats.get_target_type()
        targets = self.find_targets(simulator.characters, target_type)
        for target in targets:
            target_stats = target.get_component(Stats)
            damaged = target_stats.damaged(atk)
            target_aggro = target.get_component(Aggro)
            target_aggro.add(self.owner.id_, 1)
            simulator.log(
                '[' + self.name + '] ' + self.owner.name + 
                ' -> ' + target.name + 
                ' damaged ' + str(damaged) + 
                '(hp ' + str(target_stats.hp) + ')')
            if target_stats.is_dead():
                simulator.log(target.name + ' is dead..')
        return BehaviorTreeStatus.SUCCESS


class Spell(Skill):
    def tick(self, simulator):
        my_stats = self.owner.get_component(Stats)
        if my_stats.check_damaged():
            if self.cast_remains > 0:
                self.cast_remains += 1
                simulator.log(
                    '[' + self.name + '] ' + self.owner.name + 
                    ' casting delayed ... ' + str(self.cast_remains))
        if not self.is_casting and self.cast_time > 0:
            self.is_casting = True
            self.cast_remains = self.cast_time
            simulator.log(
                '[' + self.name + '] ' + self.owner.name + 
                ' casting ... ' + str(self.cast_remains))
            return BehaviorTreeStatus.SUCCESS
        if self.cast_remains > 0:
            self.cast_remains -= 1
            simulator.log(
                '[' + self.name + '] ' + self.owner.name + 
                ' casting ... ' + str(self.cast_remains))
            return BehaviorTreeStatus.SUCCESS
        if self.nexttime > simulator.time:
            return BehaviorTreeStatus.FAILURE
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += 1
        self.nexttime += my_stats.calc_cooltime(self.cooltime)
        #calc atk
        atk = math.floor(my_stats.calc_magic_atk() * self.power)
        #find target
        target_type = my_stats.get_target_type()
        targets = self.find_targets(simulator.characters, target_type)
        for target in targets:
            target_stats = target.get_component(Stats)
            damaged = target_stats.damaged(atk)
            target_aggro = target.get_component(Aggro)
            target_aggro.add(self.owner.id_, 1)
            simulator.log(
                '[' + self.name + '] ' + self.owner.name + 
                ' -> ' + target.name + 
                ' damaged ' + str(damaged) + 
                '(hp ' + str(target_stats.hp) + ')')
            if target_stats.is_dead():
                simulator.log(target.name + ' is dead..')
        return BehaviorTreeStatus.SUCCESS


class Heal(Skill):
    def tick(self, simulator):
        my_stats = self.owner.get_component(Stats)
        if my_stats.check_damaged():
            if self.cast_remains > 0:
                self.cast_remains += 1
                simulator.log(
                    '[' + self.name + '] ' + self.owner.name + 
                    ' casting delayed ... ' + str(self.cast_remains))
        if not self.is_casting and self.cast_time > 0:
            self.is_casting = True
            self.cast_remains = self.cast_time
            simulator.log(
                '[' + self.name + '] ' + self.owner.name + 
                ' casting ... ' + str(self.cast_remains))
            return BehaviorTreeStatus.SUCCESS
        if self.cast_remains > 0:
            self.cast_remains -= 1
            simulator.log(
                '[' + self.name + '] ' + self.owner.name + 
                ' casting ... ' + str(self.cast_remains))
            return BehaviorTreeStatus.SUCCESS
        if self.nexttime > simulator.time:
            return BehaviorTreeStatus.FAILURE
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += 1
        self.nexttime += my_stats.calc_cooltime(self.cooltime)
        targets = self.find_targets(simulator.characters, self.owner.type_)
        for target in targets:
            target_stats = target.get_component(Stats)
            if target_stats:
                amount = math.floor(my_stats.calc_magic_atk() * self.power)
                target_stats.heal(amount)
                simulator.log(
                    '[' + self.name + '] ' + self.owner.name + 
                    ' -> ' + target.name + 
                    ' amount ' + str(amount) + 
                    '(hp ' + str(target_stats.hp) + ')')
        return  BehaviorTreeStatus.SUCCESS


class Slow(Skill):
    pass


class Taunt(Skill):
    def tick(self, simulator):
        my_stats = self.owner.get_component(Stats)
        if self.nexttime > simulator.time:
            return BehaviorTreeStatus.FAILURE
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += self.power
        self.nexttime += my_stats.calc_cooltime(self.cooltime)
        simulator.log('[' + self.name + '] ' + self.owner.name)
        return  BehaviorTreeStatus.SUCCESS
