import os
import sqlite3

HERE = os.path.dirname(__file__)

DB = os.path.join(HERE, 'krenol.sqlite')

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("DELETE FROM moves")
cur.execute("DELETE FROM games")
cur.execute("DELETE FROM players")

cur.execute("DELETE FROM sqlite_sequence WHERE name='moves'")
cur.execute("DELETE FROM sqlite_sequence WHERE name='games'")
cur.execute("DELETE FROM sqlite_sequence WHERE name='players'")

conn.commit()
conn.close()
print("БД очищено і індекси скинуті.")
