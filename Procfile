release: flask db upgrade && python init_db.py
web: gunicorn --bind 0.0.0.0:$PORT app:app
worker: rq worker -u $REDIS_URL --path . default
