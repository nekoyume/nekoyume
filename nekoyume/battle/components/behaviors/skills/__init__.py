import math

from nekoyume.battle import WeightedList
from nekoyume.battle.components.bag import Bag
from nekoyume.battle.components.behaviors import Behavior
from nekoyume.battle.components.behaviors import BehaviorTreeStatus
from nekoyume.battle.components.behaviors.aggro import Aggro
from nekoyume.battle.components.stats import Stats
from nekoyume.battle.enums import AttackType, CharacterType, ItemType
from nekoyume.battle.tables import Tables


class Skill(Behavior):
    subclasses = {}

    def __init_subclass__(cls):
        super().__init_subclass__()
        Skill.subclasses[cls.__name__] = cls

    def __init__(self, name):
        self.name = name
        self.data = Tables.skills[name]
        self.nexttime = self.data.cooltime
        self.is_casting = False
        self.cast_remains = 0

    def tick(self, simulator):
        pass

    # todo: is_dead check to filter
    def find_targets(self, simulator, filter_type):
        if self.data.target_count <= 0:
            return []
        weightedlist = WeightedList()
        for target in simulator.characters:
            stats = target.get_component(Stats)
            aggro = target.get_component(Aggro)
            if filter_type == target.type_\
               and not stats.is_dead():
                weightedlist.add(target, aggro.value)
        if len(weightedlist) == 0:
            return []
        targets = []
        while len(targets) < self.data.target_count:
            targets.append(weightedlist.pop(simulator.random))
            if len(weightedlist) == 0:
                break
        return targets


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
        weapon = my_bag.get_equipped(ItemType.WEAPON)
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
        atk = math.floor(atk * (self.data.power * 0.01))
        # find target
        target_type = my_stats.get_target_type()
        targets = self.find_targets(simulator, target_type)
        for target in targets:
            target_stats = target.get_component(Stats)
            damaged = target_stats.damaged(atk)
            target_aggro = target.get_component(Aggro)
            target_aggro.add(self.owner.id_, 1)
            simulator.logger.log_attack({
                'from_type': self.owner.type_,
                'from': self.owner.to_dict(),
                'to_type': target.type_,
                'to': target.to_dict(),
                'value': damaged,
            })
            if target_stats.is_dead():
                simulator.logger.log(target.name + ' is dead..')
                if self.owner.type_ is CharacterType.PLAYER:
                    my_stats.get_exp(target_stats.data.reward_exp)
                    simulator.logger.log_exp(target_stats.data.reward_exp)
        return BehaviorTreeStatus.SUCCESS


class Spell(Skill):
    def tick(self, simulator):
        my_stats = self.owner.get_component(Stats)
        if my_stats.check_damaged():
            if self.cast_remains > 0:
                self.cast_remains += 1
                simulator.logger.log(
                    '[' + self.name + '] ' + self.owner.name
                    + ' casting delayed ... ' + str(self.cast_remains))
        if not self.is_casting and self.data.cast_time > 0:
            self.is_casting = True
            self.cast_remains = self.data.cast_time
            simulator.logger.log(
                '[' + self.name + '] ' + self.owner.name
                + ' casting ... ' + str(self.cast_remains))
            return BehaviorTreeStatus.SUCCESS
        if self.cast_remains > 0:
            self.cast_remains -= 1
            simulator.logger.log(
                '[' + self.name + '] ' + self.owner.name
                + ' casting ... ' + str(self.cast_remains))
            return BehaviorTreeStatus.SUCCESS
        if self.nexttime > simulator.time:
            return BehaviorTreeStatus.FAILURE
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += 1
        self.nexttime += my_stats.calc_cooltime(self.data.cooltime)
        atk = math.floor(my_stats.calc_magic_atk() * (self.data.power * 0.01))
        target_type = my_stats.get_target_type()
        targets = self.find_targets(simulator, target_type)
        for target in targets:
            target_stats = target.get_component(Stats)
            damaged = target_stats.damaged(atk)
            target_aggro = target.get_component(Aggro)
            target_aggro.add(self.owner.id_, 1)
            simulator.logger.log_attack({
                'from_type': self.owner.type_,
                'from': self.owner.to_dict(),
                'to_type': target.type_,
                'to': target.to_dict(),
                'value': damaged,
            })
            if target_stats.is_dead():
                simulator.logger.log(target.name + ' is dead..')
                if self.owner.type_ is CharacterType.PLAYER:
                    my_stats.get_exp(target_stats.data.reward_exp)
                    simulator.logger.log_exp(target_stats.data.reward_exp)
        return BehaviorTreeStatus.SUCCESS


class Heal(Skill):
    def tick(self, simulator):
        my_stats = self.owner.get_component(Stats)
        if my_stats.check_damaged():
            if self.cast_remains > 0:
                self.cast_remains += 1
                simulator.logger.log(
                    '[' + self.name + '] ' + self.owner.name
                    + ' casting delayed ... ' + str(self.cast_remains))
        if not self.is_casting and self.data.cast_time > 0:
            self.is_casting = True
            self.cast_remains = self.data.cast_time
            simulator.logger.log(
                '[' + self.name + '] ' + self.owner.name
                + ' casting ... ' + str(self.cast_remains))
            return BehaviorTreeStatus.SUCCESS
        if self.cast_remains > 0:
            self.cast_remains -= 1
            simulator.logger.log(
                '[' + self.name + '] ' + self.owner.name
                + ' casting ... ' + str(self.cast_remains))
            return BehaviorTreeStatus.SUCCESS
        if self.nexttime > simulator.time:
            return BehaviorTreeStatus.FAILURE
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += 1
        self.nexttime += my_stats.calc_cooltime(self.data.cooltime)
        targets = self.find_targets(simulator, self.owner.type_)
        for target in targets:
            target_stats = target.get_component(Stats)
            if target_stats:
                amount = math.floor(
                    my_stats.calc_magic_atk() * (self.data.power * 0.01))
                target_stats.heal(amount)
                simulator.logger.log_heal({
                    'from_type': self.owner.type_,
                    'from': self.owner.to_dict(),
                    'to_type': target.type_,
                    'to': target.to_dict(),
                    'value': amount,
                })
        return BehaviorTreeStatus.SUCCESS


class Slow(Skill):
    pass


class Taunt(Skill):
    def tick(self, simulator):
        my_stats = self.owner.get_component(Stats)
        if self.nexttime > simulator.time:
            return BehaviorTreeStatus.FAILURE
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += math.floor(self.data.power * 0.01)
        self.nexttime += my_stats.calc_cooltime(self.data.cooltime)
        simulator.logger.log('[' + self.name + '] ' + self.owner.name)
        return BehaviorTreeStatus.SUCCESS
