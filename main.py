from flask import request, jsonify, Flask
from flask_apscheduler import APScheduler
from flask_executor import Executor
from bson.binary import Binary

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from dotenv import load_dotenv
import os
import lzma
import sys
import mechanicalsoup
import time
import pandas as pd
import bcrypt
import datetime
import random

load_dotenv()
app = Flask(__name__)

scheduler = APScheduler()
executor = Executor(app)
running_tasks = {}


uri = os.getenv('DB_URI')
#Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)


#@scheduler.task('interval', id='interval_task', minutes=1)
#def interval_task():
#    print("This task runs every minute using interval")

@app.route("/", methods=["GET"])
def mainpage():
 
    return "こんにちは"

@app.route("/", methods=["POST"])
def startproc():
    correct = b'$2b$12$rOpsAw5/TljW23eL6iLJCupkc8XfYRLyTPpZPSE7BGcVE5HfXH9YK'
    passw = request.json.get("password")
    passw_bytes = passw.encode('utf-8')
    hashed = bcrypt.checkpw(passw_bytes, correct)
 
    if not hashed:
        return "buzi"

    task = executor.submit_stored('long_task', web_scrapper)
    running_tasks['long_task'] = task
    return jsonify({"message": "Task started", "task_id": "long_task"})

@app.route("/news", methods=["GET"])
def listnews():
    db = client['sampledb']
    
    # Get/create collection
    collection = db['index_news']
    all_documents = collection.find()

    decompressed_results = []
    for doc in all_documents:
        news_data = {}
        # Get datetime
        date = doc['datetime']
        # Decompress each news item
        for title, compressed_text in doc['news'].items():
            decompressed_text = lzma.decompress(compressed_text).decode()
            news_data[title] = decompressed_text
            
        decompressed_results.append({
            'datetime': date,
            'news': news_data
        })
    
    return decompressed_results

@app.route("/cancel", methods=["GET"])
def cancelproc():
    if 'long_task' in running_tasks:
        executor.futures.pop('long_task')
        del running_tasks['long_task']
        return jsonify({"message": "Task cancelled"})
    return jsonify({"message": "No task running"})

@app.route("/secured", methods=["post"])
def securedEndpoint():
    correct = b'$2b$12$rOpsAw5/TljW23eL6iLJCupkc8XfYRLyTPpZPSE7BGcVE5HfXH9YK'
    passw = request.json.get("password")
    passw_bytes = passw.encode('utf-8')
    hashed = bcrypt.checkpw(passw_bytes, correct)
 
    if not hashed:
        return "buzi"
    
    # Get/create database
    db = client['sampledb']
    
    # Get/create collection
    collection = db['index_news']
    all_documents = collection.find()

    decompressed_results = []
    for doc in all_documents:
        news_data = {}
        # Get datetime
        date = doc['datetime']
        # Decompress each news item
        for title, compressed_text in doc['news'].items():
            decompressed_text = lzma.decompress(compressed_text).decode()
            news_data[title] = decompressed_text
            
        decompressed_results.append({
            'datetime': date,
            'news': news_data
        })
    
    return decompressed_results
    


def web_scrapper():
    task_id = 'long_task'
    df = pd.read_csv('useragents.csv')
    browser = mechanicalsoup.StatefulBrowser()
    browser.open("https://index.hu/")

    title_and_text = {}
    titles = browser.page.select('h2.cikkcim')

    for title in titles:
        if task_id not in running_tasks:
                print("Task was cancelled")
                return "Task cancelled"

        a_tag = title.select_one('a')
        link = a_tag['href']
        if 'index.hu' in link:
            browser.set_user_agent(random.choice(df['useragent'].values))
            res = browser.follow_link(a_tag)

            while res.status_code == 429:
               
                if task_id not in running_tasks:
                    print("Task was cancelled")
                    return "Task cancelled"
            
                print("bukovári")
                time.sleep(random.randint(3, 6))

                browser = mechanicalsoup.StatefulBrowser()
                browser.set_user_agent(random.choice(df['useragent'].values))
                browser.open("https://index.hu/")

                res = browser.follow_link(a_tag)

            content_title = browser.page.select_one('div.content-title')
            article = browser.page.select_one("div.cikk-torzs")
            if content_title is None or article is None:
                continue
            
            title_and_text[content_title.get_text()] = article.get_text()
            print("stored")
          
            time.sleep(random.uniform(0, 2))

    print("stored all")
    #clean data
    title_and_text = { key.replace('\n', ''): value.replace('\n', '') for key, value in title_and_text.items() }
    print("cleaned")
    # compress data
    compressed_data = {}
    for title, text in title_and_text.items():
        #compressed_data[title] = lzma.compress(text.encode())
        compressed_data[title] = Binary(lzma.compress(text.encode()))
    print("compressed")
    try:
        # save data
        db = client['sampledb']
        
            # Get/create collection
        collection = db['index_news']
        
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc = {"datetime": date, "news": compressed_data}
        result = collection.insert_one(doc)
        print("saved")
        print(result)
    except Exception as e:
        print(e)
    



if __name__ == '__main__':
    app.config['EXECUTOR_TYPE'] = 'thread'
    app.config['EXECUTOR_PROPAGATE_EXCEPTIONS'] = True
    app.config['DEBUG'] = True
    scheduler.init_app(app)
    scheduler.start()
    app.run()