from flask_executor import Executor
from flask_apscheduler import APScheduler

scheduler = APScheduler()
executor = Executor()
running_tasks = {}