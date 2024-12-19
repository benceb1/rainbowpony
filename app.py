import db
import os
from flask import Flask
from extensions import executor, scheduler
from flask_cors import CORS
from api import mynewsapi
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())

if __name__ == "__main__":
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(mynewsapi)

    app.config['EXECUTOR_TYPE'] = 'thread'
    app.config['EXECUTOR_PROPAGATE_EXCEPTIONS'] = True
    app.config['DEBUG'] = True
    app.config['MONGO_URI'] = os.getenv('DB_URI')
    db.init_app(app)
    scheduler.init_app(app)
    scheduler.start()
    executor.init_app(app)
    app.run()



