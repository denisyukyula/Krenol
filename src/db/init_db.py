import sqlite3

conn = sqlite3.connect('src/db/krenol.sqlite')
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    player_x INTEGER,
    player_o INTEGER,
    winner TEXT,
    FOREIGN KEY(player_x) REFERENCES players(id),
    FOREIGN KEY(player_o) REFERENCES players(id)
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    move_number INTEGER,
    FOREIGN KEY(game_id) REFERENCES games(id),
    FOREIGN KEY(player_id) REFERENCES players(id)
)
''')

conn.commit()
conn.close()
print("Базу даних krenol.sqlite створено.")
