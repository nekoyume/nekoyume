# N E K O Y U M E

Nekoyume is world's first [MMORPG] based on [Blockchain].

- Nekoyume is entirely decentralized MMORPG game.
- Nekoyume uses [Dungeon World] as a basic rule.
- To use randomness on the blockchain, This project implemented
  Deterministic pseudo-random. (See the [white paper].)


## Dependencies

- Python >= 3.6
- Redis
- SQLite >= 3.16.0
- (Recommended) PostgreSQL >= 9.5


## Installation

    $ mkvirtualenv -p $(which python3.6) -a $(pwd) nekoyume
    $ pip install -e .


## Launching Node

    $ doko open


## Mining

    $ neko sleep


[MMORPG]: https://en.wikipedia.org/wiki/Massively_multiplayer_online_role-playing_game
[Blockchain]: https://en.wikipedia.org/wiki/Blockchain
[Dungeon World]: https://en.wikipedia.org/wiki/Dungeon_World
