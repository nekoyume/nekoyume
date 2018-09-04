import os
import tablib

class Table:
    def __init__(self, filename):
        dirname = os.path.join('battle', 'table') 
        d = tablib.Dataset().load(
            open(os.path.join(dirname, filename)).read()
        ).dict
        print(d)
        self.data = {}
        for i in d:
            self.data[i['id']] = i
        print(self.data)
    
    def get(self, id):
        return self.data[id]

class Tables:
    def __init__(self):
        self.stats = Table('stats.csv')
        self.monsters = Table('monsters.csv')


tables = Tables()
