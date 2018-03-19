
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

   $ pip install nekoyume


Installation for Development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

   $ git clone git@github.com:nekoyume/nekoyume.git
   $ cd nekoyume
   $ mkvirtualenv -p $(which python3.6) -a $(pwd) nekoyume
   $ pip install -e .[dev]


Launching Node
--------------

.. code-block:: console

   $ gunicorn nekoyume.app:app



Mining
------

.. code-block:: console

   $ neko


