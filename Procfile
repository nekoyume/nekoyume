web: FLASK_APP=app.py flask run --reload -p $PORT
worker: celery -A app.celery worker -l info
