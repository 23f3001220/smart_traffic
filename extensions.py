"""
Shared Flask extensions – imported by app.py and models to avoid circular imports.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
