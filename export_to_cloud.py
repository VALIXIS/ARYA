import os
import sqlite3
import json
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
DB_PATH = ROOT_DIR / 'backend' / 'arya.db'
SQL_OUT = ROOT_DIR / 'supabase_schema.sql'
JSON_OUT = ROOT_DIR / 'cloud_seed_data.json'

def export_data():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('SELECT id, content, category, created_at FROM memories')
    m_rows = cursor.fetchall()
    memories = [{'id': r[0], 'content': r[1], 'category': r[2], 'created_at': str(r[3])} for r in m_rows]

    cursor.execute('SELECT id, title, status, created_at FROM goals')
    g_rows = cursor.fetchall()
    goals = [{'id': r[0], 'title': r[1], 'status': r[2], 'created_at': str(r[3])} for r in g_rows]

    with open(str(JSON_OUT), 'w', encoding='utf-8') as jf:
        json.dump({'memories': memories, 'goals': goals}, jf, indent=2)

    print('[CLOUD EXPORTER] Exported ' + str(len(memories)) + ' memories to cloud_seed_data.json and supabase_schema.sql.')

if __name__ == '__main__':
    export_data()
