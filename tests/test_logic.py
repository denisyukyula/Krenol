import os
import sqlite3
import pytest

import src.main as main

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """
    Створює тимчасовий SQLite-файл, ініціалізує в ньому тільки таблицю moves,
    і підміняє main.DB_PATH на цей файл.
    """
    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    # Створюємо необхідну схему таблиці moves
    cur.execute('''
    CREATE TABLE moves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        x INTEGER NOT NULL,
        y INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        move_number INTEGER
    )
    ''')
    conn.commit()
    conn.close()

    # Підміна шляху до бази даних у модулі main
    monkeypatch.setattr(main, "DB_PATH", str(db_path))
    return str(db_path)


def insert_moves(moves, game_id=1):
    """
    Допоміжна функція для вставки ходів у таблицю moves.

    Аргументи:
        moves (list of tuple): список кортежів (x, y, symbol).
        game_id (int): ідентифікатор гри, для якої записуються ходи.
    """
    conn = sqlite3.connect(main.DB_PATH)
    cur = conn.cursor()
    for idx, (x, y, symbol) in enumerate(moves, start=1):
        # Вставляємо кожен хід з відповідним номером ходу
        cur.execute('''
            INSERT INTO moves (game_id, player_id, x, y, symbol, move_number)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (game_id, 1, x, y, symbol, idx))
    conn.commit()
    conn.close()


def test_horizontal_win(temp_db):
    """П’ять X підряд горизонтально дають перемогу X."""
    moves = [(0,0,'X'), (1,0,'X'), (2,0,'X'), (3,0,'X'), (4,0,'X')]
    insert_moves(moves)
    # Перевіряємо, що алгоритм виявляє горизонтальну перемогу
    assert main.check_five_in_row(1) == 'X'


def test_vertical_win(temp_db):
    """П’ять O підряд вертикально дають перемогу O."""
    moves = [(0,0,'O'), (0,1,'O'), (0,2,'O'), (0,3,'O'), (0,4,'O')]
    insert_moves(moves)
    # Алгоритм має повернути символ 'O'
    assert main.check_five_in_row(1) == 'O'


def test_diagonal_down_right_win(temp_db):
    """П’ять X по діагоналі вниз-вправо дають перемогу X."""
    moves = [(0,0,'X'), (1,1,'X'), (2,2,'X'), (3,3,'X'), (4,4,'X')]
    insert_moves(moves)
    # Перевірка основної діагоналі
    assert main.check_five_in_row(1) == 'X'


def test_diagonal_up_right_win(temp_db):
    """П’ять O по діагоналі вгору-вправо дають перемогу O."""
    moves = [(0,4,'O'), (1,3,'O'), (2,2,'O'), (3,1,'O'), (4,0,'O')]
    insert_moves(moves)
    # Перевірка зворотної діагоналі
    assert main.check_five_in_row(1) == 'O'


def test_no_win(temp_db):
    """Менше ніж п’ять в ряд — виграшу немає."""
    moves = [(0,0,'X'), (1,0,'X'), (2,0,'X'), (3,0,'X')]  # лише 4 X
    insert_moves(moves)
    # Має повернути None, оскільки лінія неповна
    assert main.check_five_in_row(1) is None


def test_overlapping_lines(temp_db):
    """Дві групи по 3 символи — перемоги нема."""
    moves = [(0,0,'X'), (1,0,'X'), (2,0,'X'), (10,10,'X'), (11,10,'X'), (12,10,'X')]
    insert_moves(moves)
    # Розрізнені лінії по 3 — перемоги немає
    assert main.check_five_in_row(1) is None
