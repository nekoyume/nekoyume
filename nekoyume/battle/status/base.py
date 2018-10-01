from dataclasses import asdict, dataclass


@dataclass
class Status:
    type: str = ''

    def __str__(self):
        return str(asdict(self))
