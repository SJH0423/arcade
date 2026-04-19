import os
import sqlite3
# v2 - arcade files restore
from flask import Flask, request, jsonify, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=None)

DB_DIR = '/app/user_data/db'
DB_PATH = os.path.join(DB_DIR, 'ranking.db')

# Local dev fallback
if not os.path.exists('/app'):
    DB_DIR = os.path.join(os.path.dirname(__file__), 'user_data', 'db')
    DB_PATH = os.path.join(DB_DIR, 'ranking.db')

os.makedirs(DB_DIR, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game TEXT NOT NULL,
            name TEXT NOT NULL,
            score INTEGER NOT NULL,
            level INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_game_score ON rankings(game, score DESC)')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            game TEXT PRIMARY KEY,
            up INTEGER DEFAULT 0,
            down INTEGER DEFAULT 0
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS voter_votes (
            voter_id TEXT NOT NULL,
            game TEXT NOT NULL,
            vote TEXT NOT NULL,
            PRIMARY KEY (voter_id, game)
        )
    ''')
    conn.execute('CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)')

    existing_cols = {row[1] for row in conn.execute('PRAGMA table_info(rankings)').fetchall()}
    if 'time' not in existing_cols:
        conn.execute('ALTER TABLE rankings ADD COLUMN time TEXT')

    conn.commit()
    conn.close()


init_db()


@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    full = os.path.join(BASE_DIR, path)
    if os.path.isdir(full):
        return send_from_directory(full, 'index.html')
    return send_from_directory(BASE_DIR, path)


@app.route('/api/ranking/<game>', methods=['GET'])
def get_ranking(game):
    limit = request.args.get('limit', 10, type=int)
    conn = get_db()
    rows = conn.execute(
        'SELECT name, score, level, time, created_at FROM rankings WHERE game=? ORDER BY score DESC LIMIT ?',
        (game, limit)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/ranking/<game>', methods=['DELETE'])
def clear_ranking(game):
    conn = get_db()
    conn.execute('DELETE FROM rankings WHERE game=?', (game,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'cleared', 'game': game})


@app.route('/api/ranking/<game>', methods=['POST'])
def add_ranking(game):
    data = request.get_json()
    if not data or 'name' not in data or 'score' not in data:
        return jsonify({'error': 'name and score required'}), 400

    name = str(data['name'])[:3].upper()
    score = int(data['score'])
    level = int(data.get('level', 1))
    time_value = data.get('time')
    time_str = str(time_value)[:16] if time_value is not None else None

    conn = get_db()
    conn.execute(
        'INSERT INTO rankings (game, name, score, level, time) VALUES (?, ?, ?, ?, ?)',
        (game, name, score, level, time_str)
    )
    conn.commit()

    # Return updated top 10
    rows = conn.execute(
        'SELECT name, score, level, time, created_at FROM rankings WHERE game=? ORDER BY score DESC LIMIT 10',
        (game,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/rating', methods=['GET'])
def get_all_ratings():
    conn = get_db()
    rows = conn.execute('SELECT game, up, down FROM ratings').fetchall()
    conn.close()
    return jsonify({r['game']: {'up': r['up'], 'down': r['down']} for r in rows})


@app.route('/api/rating/<game>', methods=['GET'])
def get_rating(game):
    conn = get_db()
    row = conn.execute('SELECT up, down FROM ratings WHERE game=?', (game,)).fetchone()
    conn.close()
    return jsonify({'up': row['up'] if row else 0, 'down': row['down'] if row else 0})


@app.route('/api/rating/<game>', methods=['POST'])
def vote_rating(game):
    data = request.get_json()
    if not data or data.get('vote') not in ('up', 'down'):
        return jsonify({'error': "vote must be 'up' or 'down'"}), 400
    voter_id = str(data.get('voter_id', '')).strip()[:64]
    if not voter_id:
        return jsonify({'error': 'voter_id required'}), 400

    new_vote = data['vote']
    conn = get_db()
    conn.execute('INSERT OR IGNORE INTO ratings (game, up, down) VALUES (?, 0, 0)', (game,))

    existing = conn.execute(
        'SELECT vote FROM voter_votes WHERE voter_id=? AND game=?',
        (voter_id, game)
    ).fetchone()

    if existing is None:
        # First vote for this voter/game
        conn.execute(f'UPDATE ratings SET {new_vote} = {new_vote} + 1 WHERE game=?', (game,))
        conn.execute(
            'INSERT INTO voter_votes (voter_id, game, vote) VALUES (?, ?, ?)',
            (voter_id, game, new_vote)
        )
        state = new_vote
    elif existing['vote'] == new_vote:
        # Re-click same = unvote
        conn.execute(f'UPDATE ratings SET {new_vote} = MAX(0, {new_vote} - 1) WHERE game=?', (game,))
        conn.execute(
            'DELETE FROM voter_votes WHERE voter_id=? AND game=?',
            (voter_id, game)
        )
        state = None
    else:
        # Switch sides
        old_vote = existing['vote']
        conn.execute(f'UPDATE ratings SET {old_vote} = MAX(0, {old_vote} - 1), {new_vote} = {new_vote} + 1 WHERE game=?', (game,))
        conn.execute(
            'UPDATE voter_votes SET vote=? WHERE voter_id=? AND game=?',
            (new_vote, voter_id, game)
        )
        state = new_vote

    conn.commit()
    row = conn.execute('SELECT up, down FROM ratings WHERE game=?', (game,)).fetchone()
    conn.close()
    return jsonify({'up': row['up'], 'down': row['down'], 'state': state})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=False)
