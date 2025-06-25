web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 300
release: python -c "from modules.database import init_db; init_db()"
