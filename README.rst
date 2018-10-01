
Nekoyume
========

|build| |coverage| |pypi| |chat| |gitter|

Nekoyume is the first `MMORPG <https://en.wikipedia.org/wiki/Massively_multiplayer_online_role-playing_game>`_ based on `blockchain <https://en.wikipedia.org/wiki/Blockchain>`_.


* Nekoyume is entirely decentralized MMORPG game.
* Nekoyume uses `Dungeon World <https://en.wikipedia.org/wiki/Dungeon_World>`_ as a basic rule.
* To achieve randomness on the blockchain, this project implements Hash random. (Read `white paper <//docs.nekoyu.me/white_paper.html>`_ for details.)

Dependencies
------------

* `Python <http://python.org/>`_ >= 3.6
* `SQLite <https://www.sqlite.org/>`_ >= 3.16.0
* `gmp <https://gmplib.org/>`_
* (Recommended) `PostgreSQL <https://www.postgresql.org/>`_ >= 9.5
* (Recommended) `Redis <https://redis.io/>`_
* (Recommended) `Docker Compose <https://docs.docker.com/compose/install/>`_

Installation
------------

Installation for development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

   $ git clone git@github.com:nekoyume/nekoyume.git
   $ cd nekoyume
   $ python3 -m venv .venv
   $ source .venv/bin/activate
   $ pip install -e .[dev,test]
   $ git config core.hooksPath hooks
   $ nekoyume init


Launching node
--------------

.. code-block:: console

   $ pip install honcho
   $ curl https://raw.githubusercontent.com/nekoyume/nekoyume/master/Procfile > Procfile
   $ PORT=5000 honcho start



Mining
------

.. code-block:: console

   $ nekoyume mine "user private key"


Running single node for development
-----------------------------------

.. code-block:: console

   $ cp .env.dist .env
   $ docker-compose build
   $ docker-compose up


.. |build| image:: https://circleci.com/gh/nekoyume/nekoyume.svg?style=shield&circle-token=fb83e926d78b99e4cda9788f3f3dce9e281270e3
    :target: https://circleci.com/gh/nekoyume/nekoyume

.. |coverage| image:: https://codecov.io/gh/nekoyume/nekoyume/branch/master/graph/badge.svg?token=VaVMWbOpm7
  :target: https://codecov.io/gh/nekoyume/nekoyume

.. |pypi| image:: https://img.shields.io/pypi/v/nekoyume.svg
  :target: https://pypi.org/project/nekoyume/

.. |chat| image:: https://img.shields.io/badge/chat-on%20telegram-brightgreen.svg
  :target: https://t.me/nekoyume

.. |deploy| image:: https://www.herokucdn.com/deploy/button.svg
  :target: https://heroku.com/deploy

.. |gitter| image:: https://badges.gitter.im/gitterHQ/gitter.png
  :target: https://gitter.im/nekoyume-dev
