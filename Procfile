web: gunicorn -b 0.0.0.0:$PORT nekoyume.app:app -w 3 -k gevent --log-level debug
worker: celery -A nekoyume.app.cel worker -l info
sync: nekoyume sync
