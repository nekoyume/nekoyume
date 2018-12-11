from dataclasses import asdict
import json


class Logger:
    def __init__(self):
        self.logs = []
        self.print = False

    def log(self, log):
        self.logs.append(log)
        if self.print:
            print(log)

    def get_dict(self):
        status = []
        for log in self.logs:
            status.append(asdict(log))
        return status

    def json_dump(self):
        return json.dumps({'status': self.get_dict()})

    def get_characters(self):
        characters = {}
        for log in self.logs:
            if log.type == 'spawn':
                characters[log.id_] = {
                    'name': log.name,
                    'type': log.character_type,
                }
        return characters
