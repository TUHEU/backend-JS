"""WSGI entry point for gunicorn: `gunicorn wsgi:app --bind ...`"""
from app import create_app

app = create_app()
