from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

DB_PATH = 'db/krenol.db'

@app.route('/')
def index():
    return render_template('index.html')

# TODO: Додати /create_game, /game/<id>, /move/<id> тощо

if __name__ == '__main__':
    app.run(debug=True)
