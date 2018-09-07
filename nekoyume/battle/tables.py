import os

class TableData(dict):
    def __init__(self, header, data):
        for i in range(len(header)):
            self[header[i]] = data[i]


class Table(dict):
    separator = '\t'
    def __init__(self, filename):
        if type(filename) == str:
            self.load(filename)
        elif type(filename) == list:
            for f in filename:
                self.load(f)
    
    def load(self, filename):
        dirname = os.path.join('battle', 'table')
        f = open(os.path.join(dirname, filename), 'r')
        text = f.read()
        f.close()
        lines = text.split('\n')
        header = lines[0].split(Table.separator)
        for line in lines[1:]:
            data = line.split(Table.separator)
            self[data[0]] = TableData(header, data)


class Tables:
    stats = Table('stats.tsv')
    monsters = Table('monsters.tsv')
    skills = Table(['skills.tsv', 'monster_skills.tsv'])
    items = Table(['items.tsv', 'item_weapons.tsv'])
