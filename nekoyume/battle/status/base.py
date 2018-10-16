from dataclasses import asdict, dataclass


@dataclass
class Status:
    type: str = ''
    time: int = 0

    def __str__(self):
        return str(asdict(self))
