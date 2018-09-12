class Logger:
    def __init__(self):
        self.logs = []

    def log_attack(self, dict_):
        dict_['type'] = 'attack'
        self.log_dict(dict_)

    def log_heal(self, dict_):
        dict_['type'] = 'heal'
        self.log_dict(dict_)

    def log_dead(self, dict_):
        dict_['type'] = 'dead'
        self.log_dict(dict_)

    def log_exp(self, exp):
        dict_ = {
            'type': 'get_exp',
            'exp': exp,
        }
        self.log_dict(dict_)

    def log_item(self, item):
        dict_ = {
            'type': 'get_item',
            'item': item,
        }
        self.log_dict(dict_)

    def log_dict(self, dict_):
        self.logs.append(dict_)

    def log(self, str_):
        pass
