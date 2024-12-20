import lzma
import pandas as pd
import random
import time
import datetime
import bcrypt
import requests
from bs4 import BeautifulSoup

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


# Create a request for datascraping
#
def create_request(url, user_agents: pd.DataFrame, ip_addresses: list[str], task_id) -> BeautifulSoup:
    print(task_id)
    if task_id not in running_tasks:
        raise Exception("Task was cancelled")

    random_proxy = random.choice(ip_addresses)
    random_user_agent = random.choice(user_agents.values)
    proxies = {
        "http://"  : random_proxy,
        "https://" : random_proxy,
        "ftp://"   : random_proxy
    }
    headers = {
        'User-Agent': random_user_agent,
    }
    session = requests.Session()
    response = session.get(url, headers=headers, proxies=proxies)
    if response.status_code == 429:
        print("429")
        time.sleep(random.uniform(3, 6))
        return create_request(url, user_agents, ip_addresses, task_id)
    return BeautifulSoup(response.content, 'html5lib')


# Datascraper algorithm
#
def get_index_main_data():
    with open('proxies.txt', 'r') as file:
        ip_addresses = [line.strip() for line in file if line.strip()]
    user_agents = pd.read_csv('useragents.csv')['useragent']
    task_id = 'long_task'
    title_and_text = {}
    soup = create_request("https://index.hu/", user_agents, ip_addresses, task_id)
    titles = soup.select('h2.cikkcim')
    try:
        for title in titles:
            if task_id not in running_tasks:
                raise Exception("Task was cancelled")

            a_tag = title.select_one('a')
            link = a_tag['href']
            if 'index.hu' in link:
                soup = create_request(link, user_agents, ip_addresses, task_id)
                content_title = soup.select_one('div.content-title')
                article = soup.select_one("div.cikk-torzs")
                if content_title is None or article is None:
                    continue

                content_title = content_title.get_text().replace('\n', '').lstrip()
                article = article.get_text().replace('\n', '').lstrip()
                title_and_text[content_title] = article
                print("Article data read successfully")
                time.sleep(random.uniform(1, 3))

        # Compress data
        compressed_data = {}
        for title, text in title_and_text.items():
            compressed_data[title] = Binary(lzma.compress(text.encode()))
        print("Compressed")

        # Save data
        db = get_db()
        collection = db['index_news']
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc = {"datetime": date, "news": compressed_data}
        result = collection.insert_one(doc)
        print("All index data successfully stored")
    except Exception as e:
        if task_id in running_tasks:
            del running_tasks['long_task']
        print(e)
    finally:
        if task_id in running_tasks:
            del running_tasks['long_task']


def get_dates():
    db = get_db()
    collection = db['index_news']
    all_documents = collection.find()
    dates = []
    for doc in all_documents:
        date = doc['datetime']
        dates.append(date)

    return dates


def check_passw(password):
    correct = b'$2b$12$rOpsAw5/TljW23eL6iLJCupkc8XfYRLyTPpZPSE7BGcVE5HfXH9YK'
    passw_bytes = password.encode('utf-8')
    return bcrypt.checkpw(passw_bytes, correct)