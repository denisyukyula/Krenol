import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, abort

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'db', 'krenol.sqlite')

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'your-secret-key'


def check_five_in_row(game_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT x, y, symbol FROM moves WHERE game_id = ?', (game_id,))
    data = cur.fetchall()
    conn.close()

    positions = {'X': set(), 'O': set()}
    for x, y, s in data:
        positions[s].add((x, y))

    dirs = [(1, 0), (0, 1), (1, 1), (1, -1)]
    for symbol in ('X', 'O'):
        coords = positions[symbol]
        for (x, y) in coords:
            for dx, dy in dirs:
                count = 1
                for mul in (1, -1):
                    nx, ny = x + dx * mul, y + dy * mul
                    while (nx, ny) in coords:
                        count += 1
                        nx += dx * mul
                        ny += dy * mul
                if count >= 5:
                    return symbol
    return None


def render_game_page(game_id, current_player_id, error_message=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('SELECT player_x, player_o, winner FROM games WHERE id = ?', (game_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        abort(404, description="Гра не знайдена")
    player_x, player_o, winner = row

    cur.execute(
        'SELECT x, y, symbol FROM moves WHERE game_id = ? ORDER BY move_number',
        (game_id,)
    )
    moves = cur.fetchall()
    conn.close()

    moves_map = {(m[0], m[1]): m[2] for m in moves}
    last_move = (moves[-1][0], moves[-1][1]) if moves else None

    PAD = 3
    initial_min = 0
    initial_max = PAD * 2  # =6

    if moves:
        xs = [m[0] for m in moves]
        ys = [m[1] for m in moves]
        min_x = max(initial_min, min(xs) - PAD)
        min_y = max(initial_min, min(ys) - PAD)
        max_x = max(initial_max, max(xs) + PAD)
        max_y = max(initial_max, max(ys) + PAD)
    else:
        min_x, min_y = initial_min, initial_min
        max_x, max_y = initial_max, initial_max

    x_coords = list(range(min_x, max_x + 1))
    y_coords = list(range(min_y, max_y + 1))

    next_symbol = 'X' if len(moves) % 2 == 0 else 'O'
    next_player_id = player_x if next_symbol == 'X' else player_o

    return render_template(
        'game.html',
        game_id=game_id,
        player_x=player_x,
        player_o=player_o,
        winner=winner,
        moves_map=moves_map,
        next_symbol=next_symbol,
        next_player_id=next_player_id,
        current_player_id=current_player_id,
        error_message=error_message,
        last_move=last_move,
        x_coords=x_coords,
        y_coords=y_coords
    )


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/create_game', methods=['POST'])
def create_game():
    username = request.form.get('username')
    if not username:
        return "Ім'я не вказано", 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('INSERT INTO players (username) VALUES (?)', (username,))
    player_x = cur.lastrowid

    cur.execute('INSERT INTO games (created_at, player_x) VALUES (?, ?)',
                (datetime.now().isoformat(), player_x))
    game_id = cur.lastrowid

    conn.commit()
    conn.close()

    return redirect(url_for('game_view',
                            game_id=game_id,
                            player_id=player_x))


@app.route('/join_game', methods=['POST'])
def join_game():
    game_id = request.form.get('game_id', type=int)
    username = request.form.get('username')
    if not game_id or not username:
        return "Неповні дані для приєднання", 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('SELECT player_o FROM games WHERE id = ?', (game_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        abort(404, description="Гра не знайдена")
    if row[0] is not None:
        conn.close()
        return "У цю гру вже приєднано двох гравців", 400

    cur.execute('INSERT INTO players (username) VALUES (?)', (username,))
    player_o = cur.lastrowid

    cur.execute('UPDATE games SET player_o = ? WHERE id = ?', (player_o, game_id))
    conn.commit()
    conn.close()

    return redirect(url_for('game_view',
                            game_id=game_id,
                            player_id=player_o))


@app.route('/game/<int:game_id>')
def game_view(game_id):
    current_player_id = request.args.get('player_id', type=int)
    return render_game_page(game_id, current_player_id)


@app.route('/move/<int:game_id>', methods=['POST'])
def make_move(game_id):
    current_player_id = (request.form.get('player_id', type=int)
                         or request.args.get('player_id', type=int))
    x_user = request.form.get('x', type=int)
    y_user = request.form.get('y', type=int)

    if x_user is None or y_user is None or current_player_id is None:
        return render_game_page(game_id, current_player_id,
                                error_message="Невірні дані ходу")

    x = x_user - 1
    y = y_user - 1

    if x < 0 or y < 0:
        return render_game_page(game_id, current_player_id,
                                error_message="Координати мають бути ≥ 1")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('SELECT player_x, player_o, winner FROM games WHERE id = ?', (game_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        abort(404, description="Гра не знайдена")
    player_x, player_o, winner = row
    if winner:
        conn.close()
        return render_game_page(game_id, current_player_id,
                                error_message=f"Гра завершена. Переможець: {winner}")
    if not player_o:
        conn.close()
        return render_game_page(game_id, current_player_id,
                                error_message="Чекаємо другого гравця")

    cur.execute('SELECT COUNT(*) FROM moves WHERE game_id = ?', (game_id,))
    move_number = cur.fetchone()[0]
    next_symbol = 'X' if move_number % 2 == 0 else 'O'
    next_player_id = player_x if next_symbol == 'X' else player_o
    if current_player_id != next_player_id:
        conn.close()
        return render_game_page(game_id, current_player_id,
                                error_message="Зараз не ваш хід")

    cur.execute('SELECT 1 FROM moves WHERE game_id = ? AND x = ? AND y = ?',
                (game_id, x, y))
    if cur.fetchone():
        conn.close()
        return render_game_page(game_id, current_player_id,
                                error_message="Клітинка вже зайнята")

    cur.execute('''
        INSERT INTO moves (game_id, player_id, x, y, symbol, move_number)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (game_id, current_player_id, x, y, next_symbol, move_number + 1))
    conn.commit()

    winner = check_five_in_row(game_id)
    if winner:
        cur.execute('UPDATE games SET winner = ? WHERE id = ?', (winner, game_id))
        conn.commit()

    conn.close()

    return redirect(url_for('game_view',
                            game_id=game_id,
                            player_id=current_player_id))


@app.route('/replays')
def replays():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
        SELECT
          g.id,
          g.created_at,
          px.username AS x_name,
          po.username AS o_name,
          g.winner
        FROM games g
        JOIN players px ON px.id = g.player_x
        JOIN players po ON po.id = g.player_o
        WHERE g.winner IS NOT NULL
        ORDER BY g.created_at DESC
    ''')
    games = cur.fetchall()
    conn.close()

    games_list = [
        {
            'id': row[0],
            'created': row[1][:19].replace('T', ' '),  # YYYY-MM-DD HH:MM:SS
            'x_name': row[2],
            'o_name': row[3],
            'winner': row[4]
        }
        for row in games
    ]
    return render_template('replays.html', games=games_list)


@app.route('/replay/<int:game_id>')
def replay(game_id):
    step = request.args.get('step', default=None, type=int)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('SELECT player_x, player_o FROM games WHERE id = ?', (game_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        abort(404, description="Гра не знайдена")
    player_x, player_o = row

    cur.execute('SELECT x, y, symbol FROM moves WHERE game_id = ? ORDER BY move_number', (game_id,))
    all_moves = cur.fetchall()
    conn.close()

    max_step = len(all_moves)
    if max_step == 0:
        return f"У грі #{game_id} ще немає ходів."

    if step is None or step < 1 or step > max_step:
        step = max_step

    moves_map = {}
    for idx, (x, y, sym) in enumerate(all_moves, start=1):
        if idx > step:
            break
        moves_map[(x, y)] = sym

    return render_template('replay.html',
                           game_id=game_id,
                           player_x=player_x,
                           player_o=player_o,
                           moves_map=moves_map,
                           step=step,
                           max_step=max_step)


@app.route('/resign/<int:game_id>', methods=['POST'])
def resign(game_id):
    player_id = (request.form.get('player_id', type=int)
                 or request.args.get('player_id', type=int))
    if player_id is None:
        abort(400, description="Невідомий гравець")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('SELECT player_x, player_o, winner FROM games WHERE id = ?', (game_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        abort(404, description="Гра не знайдена")
    player_x, player_o, winner = row

    if winner:
        conn.close()
        return redirect(url_for('game_view',
                                game_id=game_id,
                                player_id=player_id))

    if player_id == player_x:
        opponent = player_o
    elif player_id == player_o:
        opponent = player_x
    else:
        conn.close()
        abort(400, description="Ви не учасник цієї гри")

    cur.execute('UPDATE games SET winner = ? WHERE id = ?', (opponent, game_id))
    conn.commit()
    conn.close()

    return redirect(url_for('game_view',
                            game_id=game_id,
                            player_id=player_id))


if __name__ == '__main__':
    app.run(debug=True)
