# Nekoyume proof-of-concept

## Installation

    $ mkvirtualenv -p $(which python3.6) -a $(pwd) nekoyume-poc
    $ pip install -r requirements.txt
    $ cp dev.py.dist dev.py
    $ APP_SETTINGS=dev.py python app.py

