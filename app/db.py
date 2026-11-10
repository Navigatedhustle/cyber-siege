"""Small durable JSON records in SQLite WAL. No private records belong in git."""
import json
import sqlite3
from pathlib import Path
from .config import ROOT, settings

class Database:
    def __init__(self, path=None):
        self.path = str(path or ROOT / settings.database_path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript('''PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS records(kind TEXT, id TEXT, data TEXT, PRIMARY KEY(kind,id));
            CREATE TABLE IF NOT EXISTS samples(id INTEGER PRIMARY KEY, session_id TEXT, timestamp REAL, data TEXT);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, session_id TEXT, timestamp REAL, data TEXT);
            CREATE INDEX IF NOT EXISTS record_session ON records(kind,json_extract(data,'$.session_id'));
            CREATE INDEX IF NOT EXISTS sample_session ON samples(session_id,id);
            CREATE INDEX IF NOT EXISTS event_session ON events(session_id,id);
            ''')

        for suffix in ('','-wal','-shm'):
            file=Path(self.path+suffix)
            if file.exists():file.chmod(0o600)

    def connect(self):
        con = sqlite3.connect(self.path, timeout=15)
        con.execute('PRAGMA busy_timeout=15000')
        return con

    def put(self, kind, key, value):
        with self.connect() as con:
            con.execute('INSERT INTO records VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data', (kind,key,json.dumps(value)))

    def get(self, kind, key):
        with self.connect() as con:
            row = con.execute('SELECT data FROM records WHERE kind=? AND id=?', (kind,key)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, kind):
        with self.connect() as con:
            rows = con.execute('SELECT data FROM records WHERE kind=? ORDER BY rowid', (kind,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def for_session(self, kind, session_id):
        """Read only the current room, so historical rehearsals never slow phones."""
        with self.connect() as con:
            rows=con.execute("SELECT data FROM records WHERE kind=? AND json_extract(data,'$.session_id')=? ORDER BY rowid",(kind,session_id)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def delete(self, kind, key):
        with self.connect() as con:
            con.execute('DELETE FROM records WHERE kind=? AND id=?', (kind,key))

    def sample(self, session_id, timestamp, value):
        with self.connect() as con:
            con.execute('INSERT INTO samples(session_id,timestamp,data) VALUES (?,?,?)', (session_id,timestamp,json.dumps(value)))

    def samples(self, session_id):
        with self.connect() as con:
            rows = con.execute('SELECT timestamp,data FROM samples WHERE session_id=? ORDER BY id', (session_id,)).fetchall()
        return [{'timestamp':r[0], **json.loads(r[1])} for r in rows]

    def event(self, session_id, timestamp, value):
        with self.connect() as con:
            con.execute('INSERT INTO events(session_id,timestamp,data) VALUES (?,?,?)', (session_id,timestamp,json.dumps(value)))

    def events(self, session_id):
        with self.connect() as con:
            rows = con.execute('SELECT timestamp,data FROM events WHERE session_id=? ORDER BY id', (session_id,)).fetchall()
        return [{'at':r[0], **json.loads(r[1])} for r in rows]
