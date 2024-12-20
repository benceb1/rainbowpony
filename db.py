from flask import current_app, g, Flask
from flask_pymongo import PyMongo

def get_db():
    if 'db' not in g:
        g.mongo = PyMongo(current_app)
        g.db = g.mongo.db
    return g.db

def close_db(e=None):
    db = g.pop('mongo', None)
    if db is not None:
        db.cx.close()

def init_app(app: Flask):
    app.teardown_appcontext(close_db)
