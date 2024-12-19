import lzma
import pandas as pd
import mechanicalsoup
import random
import time
import datetime
import bcrypt

from db import get_db
from bson.binary import Binary
from extensions import running_tasks


def get_news():
    db = get_db()
    collection = db['index_news']
    all_documents = collection.find()

    decompressed_results = []
    for doc in all_documents:
        news_data = {}
        date = doc['datetime']
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
        compressed_data[title] = Binary(lzma.compress(text.encode()))
    print("compressed")
    try:
        # save data
        db = get_db()
        collection = db['index_news']
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc = {"datetime": date, "news": compressed_data}
        result = collection.insert_one(doc)
        print("saved")
        print(result)
    except Exception as e:
        print(e)
    
def check_passw(password):
    correct = b'$2b$12$rOpsAw5/TljW23eL6iLJCupkc8XfYRLyTPpZPSE7BGcVE5HfXH9YK'
    passw_bytes = password.encode('utf-8')
    return bcrypt.checkpw(passw_bytes, correct)