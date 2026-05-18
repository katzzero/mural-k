from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__, static_folder='/app/frontend', static_url_path='')
CORS(app)

DB_PATH = os.environ.get('KANBAN_DB', '/data/k.sqlite')
FRONTEND_DIR = '/app/frontend'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
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
    try:
        conn.execute('ALTER TABLE columns ADD COLUMN radius INTEGER DEFAULT 12')
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute('ALTER TABLE cards ADD COLUMN trashed INTEGER DEFAULT 0')
        conn.commit()
    except Exception:
        pass
    if conn.execute('SELECT COUNT(*) FROM columns').fetchone()[0] == 0:
        defaults = [('A Fazer', 0, '#ffecb3', '#ffa726', 280, '', 12), ('Em Andamento', 1, '#bbdefb', '#42a5f5', 280, '', 12), ('Concluído', 2, '#c8e6c9', '#66bb6a', 280, '', 12)]
        for title, order, bg, accent, w, h, r in defaults:
            conn.execute('INSERT INTO columns (title, order_index, background_color, accent_color, width, height, radius) VALUES (?, ?, ?, ?, ?, ?, ?)', (title, order, bg, accent, w, h, r))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/api/columns', methods=['GET'])
def get_columns():
    conn = get_db()
    rows = conn.execute('SELECT * FROM columns ORDER BY order_index').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/columns', methods=['POST'])
def create_column():
    data = request.get_json()
    conn = get_db()
    max_order = conn.execute('SELECT COALESCE(MAX(order_index), 0) FROM columns').fetchone()[0]
    cur = conn.execute(
         'INSERT INTO columns (title, order_index, background_color, accent_color, width, height) VALUES (?, ?, ?, ?, ?, ?)',
         (data['title'], max_order + 1, data.get('background_color', '#dfe1e6'), data.get('accent_color', '#90a4ae'), data.get('width', 280), data.get('height', ''))
     )
    conn.commit()
    col_id = cur.lastrowid
    row = conn.execute('SELECT * FROM columns WHERE id = ?', (col_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/columns/<int:col_id>', methods=['PUT'])
def update_column(col_id):
    data = request.get_json()
    conn = get_db()
    if 'title' in data:
        conn.execute('UPDATE columns SET title = ? WHERE id = ?', (data['title'], col_id))
    if 'order_index' in data:
        conn.execute('UPDATE columns SET order_index = ? WHERE id = ?', (data['order_index'], col_id))
    if 'background_color' in data:
        conn.execute('UPDATE columns SET background_color = ? WHERE id = ?', (data['background_color'], col_id))
    if 'accent_color' in data:
        conn.execute('UPDATE columns SET accent_color = ? WHERE id = ?', (data['accent_color'], col_id))
    if 'width' in data:
        conn.execute('UPDATE columns SET width = ? WHERE id = ?', (data['width'], col_id))
    if 'height' in data:
        conn.execute('UPDATE columns SET height = ? WHERE id = ?', (data['height'], col_id))
    if 'radius' in data:
        conn.execute('UPDATE columns SET radius = ? WHERE id = ?', (data['radius'], col_id))
    conn.commit()
    row = conn.execute('SELECT * FROM columns WHERE id = ?', (col_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/columns/<int:col_id>', methods=['DELETE'])
def delete_column(col_id):
    conn = get_db()
    conn.execute('UPDATE cards SET trashed = 1 WHERE column_id = ?', (col_id,))
    conn.execute('DELETE FROM columns WHERE id = ?', (col_id,))
    conn.commit()
    conn.close()
    return '', 204

@app.route('/api/columns/<int:col_id>/cards', methods=['GET'])
def get_cards(col_id):
    conn = get_db()
    rows = conn.execute('SELECT * FROM cards WHERE column_id = ? AND trashed = 0 ORDER BY order_index', (col_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/cards', methods=['POST'])
def create_card():
    data = request.get_json()
    conn = get_db()
    max_order = conn.execute(
        'SELECT COALESCE(MAX(order_index), 0) FROM cards WHERE column_id = ?',
        (data['column_id'],)
    ).fetchone()[0]
    cur = conn.execute(
         'INSERT INTO cards (column_id, title, description, color, order_index) VALUES (?, ?, ?, ?, ?)',
         (data['column_id'], data['title'], data.get('description', ''), data.get('color', '#ffffff'), max_order + 1)
     )
    conn.commit()
    card_id = cur.lastrowid
    row = conn.execute('SELECT * FROM cards WHERE id = ?', (card_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/cards/<int:card_id>', methods=['PUT'])
def update_card(card_id):
    data = request.get_json()
    conn = get_db()
    fields = {}
    if 'title' in data:
        fields['title'] = data['title']
    if 'description' in data:
        fields['description'] = data['description']
    if 'column_id' in data:
        fields['column_id'] = data['column_id']
    if 'color' in data:
        fields['color'] = data['color']
    if 'order_index' in data:
        fields['order_index'] = data['order_index']
    if fields:
        set_clause = ', '.join(f'{k} = ?' for k in fields)
        vals = list(fields.values()) + [card_id]
        conn.execute(f'UPDATE cards SET {set_clause} WHERE id = ?', vals)
        conn.commit()
    row = conn.execute('SELECT * FROM cards WHERE id = ?', (card_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/cards/<int:card_id>', methods=['DELETE'])
def delete_card(card_id):
    conn = get_db()
    conn.execute('UPDATE cards SET trashed = 1 WHERE id = ?', (card_id,))
    conn.commit()
    conn.close()
    return '', 204

@app.route('/api/cards/<int:card_id>/todos', methods=['GET'])
def get_todos(card_id):
    conn = get_db()
    rows = conn.execute('SELECT * FROM todos WHERE card_id = ? ORDER BY order_index', (card_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/todos', methods=['POST'])
def create_todo():
    data = request.get_json()
    conn = get_db()
    max_order = conn.execute('SELECT COALESCE(MAX(order_index), 0) FROM todos WHERE card_id = ?', (data['card_id'],)).fetchone()[0]
    cur = conn.execute(
        'INSERT INTO todos (card_id, text, checked, order_index) VALUES (?, ?, 0, ?)',
        (data['card_id'], data['text'], max_order + 1)
    )
    conn.commit()
    todo_id = cur.lastrowid
    row = conn.execute('SELECT * FROM todos WHERE id = ?', (todo_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    data = request.get_json()
    conn = get_db()
    if 'text' in data:
        conn.execute('UPDATE todos SET text = ? WHERE id = ?', (data['text'], todo_id))
    if 'checked' in data:
        conn.execute('UPDATE todos SET checked = ? WHERE id = ?', (int(data['checked']), todo_id))
    if 'order_index' in data:
        conn.execute('UPDATE todos SET order_index = ? WHERE id = ?', (data['order_index'], todo_id))
    conn.commit()
    row = conn.execute('SELECT * FROM todos WHERE id = ?', (todo_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    conn = get_db()
    conn.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
    conn.commit()
    conn.close()
    return '', 204

@app.route('/api/cards/trash', methods=['GET'])
def get_trash():
    conn = get_db()
    rows = conn.execute('SELECT * FROM cards WHERE trashed = 1 ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/cards/<int:card_id>/restore', methods=['PUT'])
def restore_card(card_id):
    conn = get_db()
    card = conn.execute('SELECT * FROM cards WHERE id = ?', (card_id,)).fetchone()
    if card:
        col_check = conn.execute('SELECT id FROM columns WHERE id = ?', (card['column_id'],)).fetchone()
        if not col_check:
            first_col = conn.execute('SELECT id FROM columns ORDER BY order_index LIMIT 1').fetchone()
            new_col_id = first_col['id'] if first_col else 1
            max_order = conn.execute('SELECT COALESCE(MAX(order_index), 0) FROM cards WHERE column_id = ?', (new_col_id,)).fetchone()[0]
            conn.execute('UPDATE cards SET trashed = 0, column_id = ?, order_index = ? WHERE id = ?',
                         (new_col_id, max_order + 1, card_id))
        else:
            conn.execute('UPDATE cards SET trashed = 0 WHERE id = ?', (card_id,))
    conn.commit()
    conn.close()
    return '', 204

@app.route('/api/cards/reorder', methods=['POST'])
def reorder_cards():
    data = request.get_json()
    conn = get_db()
    for item in data:
        conn.execute(
            'UPDATE cards SET column_id = ?, order_index = ? WHERE id = ?',
            (item['column_id'], item['order_index'], item['id'])
        )
    conn.commit()
    conn.close()
    return '', 204

@app.route('/health')
def health():
    return 'OK'

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
