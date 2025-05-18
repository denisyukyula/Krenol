import sqlite3
import pytest
from flask import url_for

import src.main as main
from src.main import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Створює тимчасовий файл БД, ініціалізує схему і повертає Flask-тест клієнт.
    """
    db_file = tmp_path / "test.sqlite"
    # Ініціалізуємо схему
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute('''
      CREATE TABLE players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL
      )
    ''')
    cur.execute('''
      CREATE TABLE games (
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
      CREATE TABLE moves (
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

    # Підміняємо шлях до БД у main
    monkeypatch.setattr(main, "DB_PATH", str(db_file))
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_create_and_join_game(client):
    """Створюємо гру та приєднуємось другим гравцем."""
    resp = client.post('/create_game', data={'username': 'Alice'})
    assert resp.status_code == 302
    loc = resp.headers['Location']
    assert 'game/1' in loc and 'player_id=1' in loc

    resp2 = client.post('/join_game', data={'game_id': 1, 'username': 'Bob'})
    assert resp2.status_code == 302
    loc2 = resp2.headers['Location']
    assert 'game/1' in loc2 and 'player_id=2' in loc2

    conn = sqlite3.connect(main.DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT player_x, player_o FROM games WHERE id = 1')
    px, po = cur.fetchone()
    conn.close()
    assert px == 1 and po == 2

def test_move_and_turn_order(client):
    """Перший ход робить X, другий — O, черги дотримуються."""
    client.post('/create_game', data={'username': 'A'})
    client.post('/join_game', data={'game_id': 1, 'username': 'B'})

    # X робить перший хід
    resp = client.post('/move/1?player_id=1', data={'x': 1, 'y': 1})
    assert resp.status_code == 302

    conn = sqlite3.connect(main.DB_PATH)
    cur = conn.cursor()
    cur.execute(
        'SELECT x, y, symbol, move_number FROM moves WHERE game_id=1 ORDER BY id'
    )
    r = cur.fetchone()
    conn.close()
    assert r == (0, 0, 'X', 1)

    # X намагається ходити вдруге — помилка
    resp2 = client.post('/move/1?player_id=1', data={'x': 2, 'y': 2})
    text2 = resp2.get_data(as_text=True)
    assert "Зараз не ваш хід" in text2

    # O робить хід
    resp3 = client.post('/move/1?player_id=2', data={'x': 2, 'y': 1})
    assert resp3.status_code == 302

def test_forfeit(client):
    """Кнопка 'Здатися' фіксує переможцем опонента."""
    client.post('/create_game', data={'username': 'X'})
    client.post('/join_game', data={'game_id': 1, 'username': 'O'})

    resp = client.post('/resign/1?player_id=1')
    assert resp.status_code == 302

    conn = sqlite3.connect(main.DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT winner FROM games WHERE id=1')
    winner = cur.fetchone()[0]
    conn.close()
    assert int(winner) == 2  # player_o

def test_replays_and_replay_view(client):
    """Перегляд списку та покроковий реплей."""
    # Створюємо гру та приєднуємо другого гравця
    client.post('/create_game', data={'username': 'A'})
    client.post('/join_game', data={'game_id': 1, 'username': 'B'})
    # Робимо 5 ходів X по горизонталі, O водночас ходить у віддалені координати
    for i in range(5):
        client.post(f'/move/1?player_id=1', data={'x': i+1, 'y': 1})
        client.post(f'/move/1?player_id=2', data={'x': 100+i, 'y': 100})

    # Список реплеїв
    resp = client.get('/replays')
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Переглянути" in text

    # Реплей крок 3
    resp2 = client.get('/replay/1?step=3')
    assert resp2.status_code == 200
    # Має бути принаймні 3 клітинки з ходами
    assert resp2.get_data(as_text=True).count('<td') >= 3
