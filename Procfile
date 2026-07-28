release: flask db upgrade
web: gunicorn run:app --workers 3 --timeout 60 --bind 0.0.0.0:$PORT