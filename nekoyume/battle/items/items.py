from tables import Tables


class Item:
    subclasses = {}
    def __init_subclass__(cls):
        super().__init_subclass__()
        Item.subclasses[cls.__name__] = cls

    def __init__(self, name):
        self.name = name
        data = Tables.items[name]
        self.stack = int(data['stack'])
        self.param_0 = int(data['param_0'])


class Equipment(Item):
    def __init__(self, name):
        super().__init__(name)
        #stats
