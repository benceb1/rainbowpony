from flask import Blueprint, request, jsonify
from flask_cors import CORS
from index_news_service import get_news, get_index_main_data, check_passw, get_dates
from extensions import executor, running_tasks


mynewsapi = Blueprint('mynewsapi', 'mynewsapi')
CORS(mynewsapi)

@mynewsapi.route("/", methods=["GET"])
def mainpage():
    return "こんにちは"

@mynewsapi.route('/index_news', methods=['GET'])
def get_index_news():
    return get_news()

@mynewsapi.route('/index_dates', methods=['GET'])
def get_index_list():
    return get_dates()


@mynewsapi.route("/start", methods=["POST"])
def startproc():
    correct = check_passw(request.json.get("password"))
    if not correct:
        return ">:@"

    task = executor.submit_stored('long_task', get_index_main_data)
    running_tasks['long_task'] = task
    return jsonify({"message": "Task started", "task_id": "long_task"})

@mynewsapi.route("/cancel", methods=["POST"])
def cancelproc():
    correct = check_passw(request.json.get("password"))
    if not correct:
        return ">:@"
    
    if 'long_task' in running_tasks:
        executor.futures.pop('long_task')
        del running_tasks['long_task']
        return jsonify({"message": "Task cancelled"})
    return jsonify({"message": "No task running"})