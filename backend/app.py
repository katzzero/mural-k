from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.environ.get('KANBAN_FRONTEND',
    '/app/frontend' if os.path.isdir('/app/frontend')
    else os.path.join(BASE_DIR, 'frontend'))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

DB_PATH = os.environ.get('KANBAN_DB',
    '/data/k.sqlite' if os.path.isdir('/data')
    else os.path.join(BASE_DIR, 'data', 'k.sqlite'))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def get_json():
    data = request.get_json(silent=True)
    if data is None:
        return None, ('Invalid JSON', 400)
    return data, None

def init_db():
    conn = get_db()
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS columns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            background_color TEXT DEFAULT '#dfe1e6',
            accent_color TEXT DEFAULT '#90a4ae',
            width INTEGER DEFAULT 280,
            height TEXT DEFAULT '',
            radius INTEGER DEFAULT 12
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            column_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            color TEXT DEFAULT '#ffffff',
            order_index INTEGER NOT NULL,
            trashed INTEGER DEFAULT 0,
            done INTEGER DEFAULT 0,
            deadline TEXT,
            FOREIGN KEY (column_id) REFERENCES columns(id) ON DELETE CASCADE
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            checked INTEGER DEFAULT 0,
            order_index INTEGER NOT NULL,
            FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
        )''')
        # migrations for existing databases
        for migration in [
            ("ALTER TABLE columns ADD COLUMN radius INTEGER DEFAULT 12",),
            ("ALTER TABLE cards ADD COLUMN trashed INTEGER DEFAULT 0",),
            ("ALTER TABLE cards ADD COLUMN done INTEGER DEFAULT 0",),
            ("ALTER TABLE cards ADD COLUMN deadline TEXT",),
        ]:
            try:
                conn.execute(migration[0])
                conn.commit()
            except sqlite3.OperationalError:
                pass
        if conn.execute('SELECT COUNT(*) FROM columns').fetchone()[0] == 0:
            defaults = [('A Fazer', 0, '#ffecb3', '#ffa726', 280, '', 12), ('Em Andamento', 1, '#bbdefb', '#42a5f5', 280, '', 12), ('Concluído', 2, '#c8e6c9', '#66bb6a', 280, '', 12)]
            for title, order, bg, accent, w, h, r in defaults:
                conn.execute('INSERT INTO columns (title, order_index, background_color, accent_color, width, height, radius) VALUES (?, ?, ?, ?, ?, ?, ?)', (title, order, bg, accent, w, h, r))
        conn.commit()
    finally:
        conn.close()

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/api/columns', methods=['GET'])
def get_columns():
    conn = get_db()
    try:
        rows = conn.execute('SELECT * FROM columns ORDER BY order_index').fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route('/api/columns', methods=['POST'])
def create_column():
    data, err = get_json()
    if err:
        return jsonify({'error': err[0]}), err[1]
    if not data or 'title' not in data:
        return jsonify({'error': 'title is required'}), 400
    title = data['title'].strip()
    if not title:
        return jsonify({'error': 'title cannot be empty'}), 400
    conn = get_db()
    try:
        max_order = conn.execute('SELECT COALESCE(MAX(order_index), 0) FROM columns').fetchone()[0]
        cur = conn.execute(
            'INSERT INTO columns (title, order_index, background_color, accent_color, width, height) VALUES (?, ?, ?, ?, ?, ?)',
            (title, max_order + 1, data.get('background_color', '#dfe1e6'), data.get('accent_color', '#90a4ae'), data.get('width', 280), data.get('height', ''))
        )
        conn.commit()
        col_id = cur.lastrowid
        row = conn.execute('SELECT * FROM columns WHERE id = ?', (col_id,)).fetchone()
        return jsonify(dict(row)), 201
    finally:
        conn.close()

@app.route('/api/columns/<int:col_id>', methods=['PUT'])
def update_column(col_id):
    data, err = get_json()
    if err:
        return jsonify({'error': err[0]}), err[1]
    if not data:
        return jsonify({'error': 'request body is required'}), 400
    conn = get_db()
    try:
        allowed_fields = {'title', 'order_index', 'background_color', 'accent_color', 'width', 'height', 'radius'}
        fields = {k: v for k, v in data.items() if k in allowed_fields}
        if not fields:
            return jsonify({'error': 'no valid fields to update'}), 400
        set_clause = ', '.join(f'{k} = ?' for k in fields)
        vals = list(fields.values()) + [col_id]
        conn.execute(f'UPDATE columns SET {set_clause} WHERE id = ?', vals)
        conn.commit()
        row = conn.execute('SELECT * FROM columns WHERE id = ?', (col_id,)).fetchone()
        if not row:
            return jsonify({'error': 'column not found'}), 404
        return jsonify(dict(row))
    finally:
        conn.close()

@app.route('/api/columns/<int:col_id>', methods=['DELETE'])
def delete_column(col_id):
    conn = get_db()
    try:
        conn.execute('UPDATE cards SET trashed = 1 WHERE column_id = ?', (col_id,))
        conn.execute('DELETE FROM columns WHERE id = ?', (col_id,))
        conn.commit()
        return '', 204
    finally:
        conn.close()

@app.route('/api/columns/<int:col_id>/cards', methods=['GET'])
def get_cards(col_id):
    conn = get_db()
    try:
        rows = conn.execute('SELECT * FROM cards WHERE column_id = ? AND trashed = 0 ORDER BY order_index', (col_id,)).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route('/api/cards', methods=['GET'])
def get_all_cards():
    conn = get_db()
    try:
        rows = conn.execute('SELECT * FROM cards WHERE trashed = 0 ORDER BY column_id, order_index').fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route('/api/cards', methods=['POST'])
def create_card():
    data, err = get_json()
    if err:
        return jsonify({'error': err[0]}), err[1]
    if not data or 'column_id' not in data or 'title' not in data:
        return jsonify({'error': 'column_id and title are required'}), 400
    conn = get_db()
    try:
        col = conn.execute('SELECT id FROM columns WHERE id = ?', (data['column_id'],)).fetchone()
        if not col:
            return jsonify({'error': 'column not found'}), 404
        max_order = conn.execute(
            'SELECT COALESCE(MAX(order_index), 0) FROM cards WHERE column_id = ?',
            (data['column_id'],)
        ).fetchone()[0]
        cur = conn.execute(
            'INSERT INTO cards (column_id, title, description, color, deadline, order_index) VALUES (?, ?, ?, ?, ?, ?)',
            (data['column_id'], data['title'], data.get('description', ''), data.get('color', '#ffffff'), data.get('deadline'), max_order + 1)
        )
        conn.commit()
        card_id = cur.lastrowid
        row = conn.execute('SELECT * FROM cards WHERE id = ?', (card_id,)).fetchone()
        return jsonify(dict(row)), 201
    finally:
        conn.close()

@app.route('/api/cards/<int:card_id>', methods=['PUT'])
def update_card(card_id):
    data, err = get_json()
    if err:
        return jsonify({'error': err[0]}), err[1]
    if not data:
        return jsonify({'error': 'request body is required'}), 400
    conn = get_db()
    try:
        allowed_fields = {'title', 'description', 'column_id', 'color', 'done', 'deadline', 'order_index'}
        fields = {}
        for k, v in data.items():
            if k not in allowed_fields:
                continue
            if k == 'done':
                fields[k] = int(v)
            else:
                fields[k] = v
        if not fields:
            return jsonify({'error': 'no valid fields to update'}), 400
        set_clause = ', '.join(f'{k} = ?' for k in fields)
        vals = list(fields.values()) + [card_id]
        conn.execute(f'UPDATE cards SET {set_clause} WHERE id = ?', vals)
        conn.commit()
        row = conn.execute('SELECT * FROM cards WHERE id = ?', (card_id,)).fetchone()
        if not row:
            return jsonify({'error': 'card not found'}), 404
        return jsonify(dict(row))
    finally:
        conn.close()

@app.route('/api/cards/<int:card_id>', methods=['DELETE'])
def delete_card(card_id):
    conn = get_db()
    try:
        conn.execute('UPDATE cards SET trashed = 1 WHERE id = ?', (card_id,))
        conn.commit()
        return '', 204
    finally:
        conn.close()

@app.route('/api/cards/<int:card_id>/todos', methods=['GET'])
def get_todos(card_id):
    conn = get_db()
    try:
        rows = conn.execute('SELECT * FROM todos WHERE card_id = ? ORDER BY order_index', (card_id,)).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route('/api/todos', methods=['POST'])
def create_todo():
    data, err = get_json()
    if err:
        return jsonify({'error': err[0]}), err[1]
    if not data or 'card_id' not in data or 'text' not in data:
        return jsonify({'error': 'card_id and text are required'}), 400
    conn = get_db()
    try:
        card = conn.execute('SELECT id FROM cards WHERE id = ?', (data['card_id'],)).fetchone()
        if not card:
            return jsonify({'error': 'card not found'}), 404
        max_order = conn.execute('SELECT COALESCE(MAX(order_index), 0) FROM todos WHERE card_id = ?', (data['card_id'],)).fetchone()[0]
        cur = conn.execute(
            'INSERT INTO todos (card_id, text, checked, order_index) VALUES (?, ?, 0, ?)',
            (data['card_id'], data['text'], max_order + 1)
        )
        conn.commit()
        todo_id = cur.lastrowid
        row = conn.execute('SELECT * FROM todos WHERE id = ?', (todo_id,)).fetchone()
        return jsonify(dict(row)), 201
    finally:
        conn.close()

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    data, err = get_json()
    if err:
        return jsonify({'error': err[0]}), err[1]
    if not data:
        return jsonify({'error': 'request body is required'}), 400
    conn = get_db()
    try:
        allowed_fields = {'text', 'checked', 'order_index'}
        fields = {}
        for k, v in data.items():
            if k not in allowed_fields:
                continue
            if k == 'checked':
                fields[k] = int(v)
            else:
                fields[k] = v
        if not fields:
            return jsonify({'error': 'no valid fields to update'}), 400
        set_clause = ', '.join(f'{k} = ?' for k in fields)
        vals = list(fields.values()) + [todo_id]
        conn.execute(f'UPDATE todos SET {set_clause} WHERE id = ?', vals)
        conn.commit()
        row = conn.execute('SELECT * FROM todos WHERE id = ?', (todo_id,)).fetchone()
        if not row:
            return jsonify({'error': 'todo not found'}), 404
        return jsonify(dict(row))
    finally:
        conn.close()

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        conn.commit()
        return '', 204
    finally:
        conn.close()

@app.route('/api/cards/trash', methods=['GET'])
def get_trash():
    conn = get_db()
    try:
        rows = conn.execute('SELECT * FROM cards WHERE trashed = 1 ORDER BY id DESC').fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@app.route('/api/cards/<int:card_id>/restore', methods=['PUT'])
def restore_card(card_id):
    conn = get_db()
    try:
        card = conn.execute('SELECT * FROM cards WHERE id = ?', (card_id,)).fetchone()
        if not card:
            return jsonify({'error': 'card not found'}), 404
        col_check = conn.execute('SELECT id FROM columns WHERE id = ?', (card['column_id'],)).fetchone()
        if not col_check:
            first_col = conn.execute('SELECT id FROM columns ORDER BY order_index LIMIT 1').fetchone()
            if not first_col:
                return jsonify({'error': 'no columns available'}), 400
            new_col_id = first_col['id']
            max_order = conn.execute('SELECT COALESCE(MAX(order_index), 0) FROM cards WHERE column_id = ?', (new_col_id,)).fetchone()[0]
            conn.execute('UPDATE cards SET trashed = 0, column_id = ?, order_index = ? WHERE id = ?',
                         (new_col_id, max_order + 1, card_id))
        else:
            conn.execute('UPDATE cards SET trashed = 0 WHERE id = ?', (card_id,))
        conn.commit()
        return '', 204
    finally:
        conn.close()

@app.route('/api/cards/reorder', methods=['POST'])
def reorder_cards():
    data, err = get_json()
    if err:
        return jsonify({'error': err[0]}), err[1]
    if not data or not isinstance(data, list):
        return jsonify({'error': 'array of card objects is required'}), 400
    conn = get_db()
    try:
        for item in data:
            if 'id' not in item or 'column_id' not in item or 'order_index' not in item:
                return jsonify({'error': 'each item must have id, column_id, and order_index'}), 400
            conn.execute(
                'UPDATE cards SET column_id = ?, order_index = ? WHERE id = ?',
                (item['column_id'], item['order_index'], item['id'])
            )
        conn.commit()
        return '', 204
    finally:
        conn.close()

@app.route('/api/reset', methods=['POST'])
def reset_all():
    conn = get_db()
    try:
        conn.execute('DELETE FROM todos')
        conn.execute('DELETE FROM cards')
        conn.execute('DELETE FROM columns')
        conn.execute("INSERT INTO columns (title, order_index, background_color, accent_color, width, height, radius) VALUES ('A Fazer', 0, '#ffecb3', '#ffa726', 280, '', 12)")
        conn.execute("INSERT INTO columns (title, order_index, background_color, accent_color, width, height, radius) VALUES ('Em Andamento', 1, '#bbdefb', '#42a5f5', 280, '', 12)")
        conn.execute("INSERT INTO columns (title, order_index, background_color, accent_color, width, height, radius) VALUES ('Concluído', 2, '#c8e6c9', '#66bb6a', 280, '', 12)")
        conn.commit()
        return jsonify({'ok': True}), 200
    finally:
        conn.close()

@app.route('/api/cards/trash/clear', methods=['DELETE'])
def clear_trash():
    conn = get_db()
    try:
        conn.execute('DELETE FROM todos WHERE card_id IN (SELECT id FROM cards WHERE trashed = 1)')
        conn.execute('DELETE FROM cards WHERE trashed = 1')
        conn.commit()
        return '', 204
    finally:
        conn.close()

@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
