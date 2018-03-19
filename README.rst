
Nekoyume
========

Nekoyume is world's first `MMORPG <https://en.wikipedia.org/wiki/Massively_multiplayer_online_role-playing_game>`_ based on `Blockchain <https://en.wikipedia.org/wiki/Blockchain>`_.


* Nekoyume is entirely decentralized MMORPG game.
* Nekoyume uses `Dungeon World <https://en.wikipedia.org/wiki/Dungeon_World>`_ as a basic rule.
* To use randomness on the blockchain, This project implemented Hash random.
  (see :doc:`white paper <white_paper_ko>`.)

Dependencies
------------


* Python >= 3.6
* Redis
* SQLite >= 3.16.0
* (Recommended) PostgreSQL >= 9.5

Installation
------------

.. code-block:: console

   $ mkvirtualenv -p $(which python3.6) -a $(pwd) nekoyume
   $ pip install -r requirements.txt



Launching Node
--------------

.. code-block:: console

   $ PORT=5000 honcho start



Mining
------

.. code-block:: console

   $ python neko.py


