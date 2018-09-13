class WeightedList:
    def __init__(self):
        self.values_ = []
        self.weights_ = []

    def __len__(self):
        return len(self.values_)

    def __str__(self):
        return str((self.values_, self.weights_))

    def add(self, value, weight):
        self.values_.append(value)
        self.weights_.append(weight)

    def select(self, random, pop=False):
        if not self.values_:
            return None
        weight_sum = 0
        for i in self.weights_:
            weight_sum += i
        rnd = random.randint(0, weight_sum - 1)
        idx = -1
        for i in range(len(self.values_)):
            if rnd < self.weights_[i]:
                idx = i
                break
            rnd -= self.weights_[i]
        if idx < 0:
            return None
        ret = self.values_[idx]
        if pop:
            del self.values_[i]
            del self.weights_[i]
        return ret

    def pop(self, random):
        return self.select(random, True)
