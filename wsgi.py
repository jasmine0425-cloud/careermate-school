"""Production entry point: gunicorn wsgi:app."""
from app import app, init_db

init_db()
