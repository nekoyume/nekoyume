from . import Behavior, BehaviorTreeStatus


class Aggro(Behavior):
    def __init__(self):
        self.value = 1  # my global aggro
        self.targets = {}  # target aggro

    def tick(self, simulator):
        self.value = max(1, self.value - 1)
        for v in self.targets:
            self.targets[v] = max(0, self.targets[v] - 1)
        return BehaviorTreeStatus.SUCCESS

    def add(self, target_id, value):
        if target_id in self.targets:
            self.targets[target_id] += value
        else:
            self.targets[target_id] = value
