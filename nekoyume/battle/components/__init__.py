from ..utils import itersubclasses


class ComponentContainer:
    def __init__(self):
        self.components = []

    def add_component(self, comp):
        comp.owner = self
        self.components.append(comp)
        return comp

    def remove_component(self, comp):
        comp.owner = None
        self.components.remove(comp)

    def get_component(self, cls):
        for comp in self.components:
            if comp.__class__ == cls:
                return comp
        subclasses = itersubclasses(cls)
        for subcls in subclasses:
            for comp in self.components:
                    if comp.__class__ == subcls:
                        return comp

    def get_components(self, cls):
        ret = []
        subclasses = itersubclasses(cls)
        for subcls in subclasses:
            for comp in self.components:
                    if comp.__class__ == subcls:
                        ret.append(comp)
        return ret


class Component:
    def __init__(self):
        self.owner = None

    def send_message(self, msg):
        for comp in self.owner.components:
            if not comp == self:
                comp.on_message(msg)

    def on_message(self, msg):
        # override me if need
        pass
