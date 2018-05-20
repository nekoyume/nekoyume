
Nekoyume
========

|build| |coverage|

Nekoyume is world's first `MMORPG <https://en.wikipedia.org/wiki/Massively_multiplayer_online_role-playing_game>`_ based on `Blockchain <https://en.wikipedia.org/wiki/Blockchain>`_.


* Nekoyume is entirely decentralized MMORPG game.
* Nekoyume uses `Dungeon World <https://en.wikipedia.org/wiki/Dungeon_World>`_ as a basic rule.
* To use randomness on the blockchain, This project implemented Hash random. (see `white paper <//docs.nekoyu.me/white_paper.html>`_.)

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
   $ nekoyume init


Installation for Development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

   $ git clone git@github.com:nekoyume/nekoyume.git
   $ cd nekoyume
   $ mkvirtualenv -p $(which python3.6) -a $(pwd) nekoyume
   $ pip install -e .[dev,test]


Launching Node
--------------

.. code-block:: console

   $ pip install honcho
   $ curl https://cdn.rawgit.com/nekoyume/nekoyume/master/Procfile > Procfile
   $ PORT=5000 honcho start



Mining
------

.. code-block:: console

   $ nekoyume neko


.. |build| image:: https://circleci.com/gh/nekoyume/nekoyume.svg?style=shield&circle-token=fb83e926d78b99e4cda9788f3f3dce9e281270e3
    :target: https://circleci.com/gh/nekoyume/nekoyume

.. |coverage| image:: https://codecov.io/gh/nekoyume/nekoyume/branch/master/graph/badge.svg?token=VaVMWbOpm7
  :target: https://codecov.io/gh/nekoyume/nekoyume
