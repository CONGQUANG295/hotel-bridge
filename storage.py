"""SQLite persistence for the Hotel Bridge pilot API.

The public server contract remains a simple state dictionary so the existing
prototype routes can migrate without a frontend rewrite. The legacy JSON file
is imported once when the database is empty and retained as a backup.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
DB_FILE = ROOT / "hotel-bridge.db"
LEGACY_FILE = ROOT / "pilot-state.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  room TEXT NOT NULL,
  service_id TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  room TEXT NOT NULL,
  mine INTEGER NOT NULL,
  name TEXT NOT NULL,
  original TEXT NOT NULL,
  translated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  room TEXT NOT NULL,
  language TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
  id TEXT PRIMARY KEY,
  action TEXT NOT NULL,
  room TEXT NOT NULL,
  detail TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS staff_sessions (
  token TEXT PRIMARY KEY,
  username TEXT NOT NULL,
  role TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
"""


def connect():
    connection = sqlite3.connect(DB_FILE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def _count(connection, table):
    return connection.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]


def _migrate_legacy(connection):
    if not LEGACY_FILE.exists() or any(_count(connection, table) for table in ("orders", "messages", "sessions", "audit")):
        return False
    try:
        legacy = json.loads(LEGACY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    for order in legacy.get("orders", []):
        connection.execute("INSERT OR IGNORE INTO orders VALUES (?, ?, ?, ?, ?, ?)", (order["id"], order["room"], order["service_id"], order.get("quantity", 1), order["status"], order["created_at"]))
    for message in legacy.get("messages", []):
        connection.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?, ?)", (message["id"], message["room"], int(message.get("mine", False)), message["name"], message["original"], message["translated"]))
    for session in legacy.get("sessions", []):
        connection.execute("INSERT OR IGNORE INTO sessions VALUES (?, ?, ?, ?, ?)", (session["token"], session["room"], session["language"], session["created_at"], session["expires_at"]))
    for event in legacy.get("audit", []):
        connection.execute("INSERT OR IGNORE INTO audit VALUES (?, ?, ?, ?, ?)", (event["id"], event["action"], event["room"], event.get("detail", ""), event["created_at"]))
    return True


def load_state():
    with connect() as connection:
        _migrate_legacy(connection)
        orders = [dict(row) for row in connection.execute("SELECT id, room, service_id, quantity, status, created_at FROM orders ORDER BY rowid DESC")]
        messages = []
        for row in connection.execute("SELECT id, room, mine, name, original, translated FROM messages ORDER BY rowid ASC"):
            item = dict(row)
            item["mine"] = bool(item["mine"])
            messages.append(item)
        sessions = [dict(row) for row in connection.execute("SELECT token, room, language, created_at, expires_at FROM sessions ORDER BY rowid ASC")]
        audit = [dict(row) for row in connection.execute("SELECT id, action, room, detail, created_at FROM audit ORDER BY rowid ASC")]
        staff_sessions = [dict(row) for row in connection.execute("SELECT token, username, role, created_at, expires_at FROM staff_sessions ORDER BY rowid ASC")]
        return {"orders": orders, "messages": messages, "sessions": sessions, "audit": audit, "staff_sessions": staff_sessions}


def save_state(state):
    with connect() as connection:
        connection.execute("DELETE FROM orders")
        connection.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", [(o["id"], o["room"], o["service_id"], int(o.get("quantity", 1)), o["status"], o["created_at"]) for o in state.get("orders", [])])
        connection.execute("DELETE FROM messages")
        connection.executemany("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)", [(m["id"], m["room"], int(m.get("mine", False)), m["name"], m["original"], m["translated"]) for m in state.get("messages", [])])
        connection.execute("DELETE FROM sessions")
        connection.executemany("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)", [(s["token"], s["room"], s["language"], s["created_at"], s["expires_at"]) for s in state.get("sessions", [])])
        connection.execute("DELETE FROM audit")
        connection.executemany("INSERT INTO audit VALUES (?, ?, ?, ?, ?)", [(a["id"], a["action"], a["room"], a.get("detail", ""), a["created_at"]) for a in state.get("audit", [])])
        connection.execute("DELETE FROM staff_sessions")
        connection.executemany("INSERT INTO staff_sessions VALUES (?, ?, ?, ?, ?)", [(s["token"], s["username"], s["role"], s["created_at"], s["expires_at"]) for s in state.get("staff_sessions", [])])


def database_summary():
    with connect() as connection:
        return {table: _count(connection, table) for table in ("orders", "messages", "sessions", "audit", "staff_sessions")}
