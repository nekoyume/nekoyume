class Logger:
    def __init__(self):
        self.logs = []
        self.print = False

    def log_attack(self, dict_):
        dict_['type'] = 'attack'
        self.log(dict_)

    def log_heal(self, dict_):
        dict_['type'] = 'heal'
        self.log(dict_)

    def log_dead(self, dict_):
        dict_['type'] = 'dead'
        self.log(dict_)

    def log_exp(self, exp):
        dict_ = {
            'type': 'get_exp',
            'exp': exp,
        }
        self.log(dict_)

    def log_item(self, item):
        dict_ = {
            'type': 'get_item',
            'item': item,
        }
        self.log(dict_)

    def log(self, log):
        self.logs.append(log)
        if self.print:
            print(log)
