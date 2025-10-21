release: python init_db.py
web: gunicorn app:app
worker: rq worker -u $REDIS_URL --path . default
