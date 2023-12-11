import time
import mysql.connector
from flask import Flask
from main import app
from main import db_init
import main
from gunicorn.app.base import BaseApplication
import os
import dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import json
import domains

dotenv.load_dotenv()
db_config = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

class GunicornApp(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

def establish_database_connection():
    while True:
        try:
            conn = mysql.connector.connect(**db_config)
            if conn.is_connected():
                print('Connected to database')
                break
        except mysql.connector.Error as e:
            print('Connecting to database...', e)
        time.sleep(1)
    conn.close()



if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(domains.syncDomains, 'cron', hour='*')
    scheduler.start()

    establish_database_connection()
    db_init()
    workers = os.getenv('WORKERS')
    threads = os.getenv('THREADS')
    if workers is None:
        workers = 1
    if threads is None:
        threads = 2
    workers = int(workers)
    threads = int(threads)
    options = {
        'bind': '0.0.0.0:5000',
        'workers': workers,
        'threads': threads,
    }
    gunicorn_app = GunicornApp(app, options)
    print('Starting server with ' + str(workers) + ' workers and ' + str(threads) + ' threads', flush=True)
    gunicorn_app.run()
