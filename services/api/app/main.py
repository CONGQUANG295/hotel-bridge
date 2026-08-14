from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

Role = Literal["front_desk", "housekeeping", "restaurant", "maintenance", "manager"]

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = Path(os.getenv("HOTEL_BRIDGE_DB", ROOT / "hotel-bridge.db"))

SERVICES = [
    {"id": "towels", "name": "Extra towels", "localizedName": "Thêm khăn tắm", "department": "housekeeping", "etaMinutes": 15, "priceLabel": "Complimentary"},
    {"id": "room-service", "name": "Room service", "localizedName": "Đồ ăn tại phòng", "department": "restaurant", "etaMinutes": 35, "priceLabel": "From $8"},
    {"id": "maintenance", "name": "Room maintenance", "localizedName": "Báo hỏng thiết bị", "department": "maintenance", "etaMinutes": 20, "priceLabel": "Complimentary"},
]
STATUSES = {"NEW", "ACCEPTED", "IN_PROGRESS", "READY", "DELIVERED", "COMPLETED", "CANCELLED", "ESCALATED"}

app = FastAPI(title="Hotel Bridge API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:3001"], allow_methods=["*"], allow_headers=["*"])


def now() -> datetime:
    return datetime.now(timezone.utc)


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript("""
      CREATE TABLE IF NOT EXISTS guest_sessions (
        token TEXT PRIMARY KEY, room_number TEXT NOT NULL, locale TEXT NOT NULL,
        expires_at TEXT NOT NULL, created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY, room_number TEXT NOT NULL, service_id TEXT NOT NULL,
        quantity INTEGER NOT NULL, note TEXT NOT NULL, status TEXT NOT NULL,
        assigned_role TEXT NOT NULL, due_at TEXT NOT NULL, created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL, session_token TEXT NOT NULL REFERENCES guest_sessions(token)
      );
      CREATE TABLE IF NOT EXISTS audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL, action TEXT NOT NULL, actor TEXT NOT NULL,
        created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY, session_token TEXT NOT NULL REFERENCES guest_sessions(token),
        room_number TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id),
        sender TEXT NOT NULL, original_text TEXT NOT NULL, translated_text TEXT NOT NULL,
        source_locale TEXT NOT NULL, target_locale TEXT NOT NULL, created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS staff_users (
        id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL,
        role TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS staff_tokens (
        token_hash TEXT PRIMARY KEY, staff_id TEXT NOT NULL REFERENCES staff_users(id),
        expires_at TEXT NOT NULL, created_at TEXT NOT NULL
      );
    """)
    bootstrap_staff(connection)
    return connection


class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str


class SessionRequest(BaseModel):
    roomNumber: str = Field(min_length=1, max_length=20)
    locale: str = Field(default="en", min_length=2, max_length=10)


class OrderRequest(BaseModel):
    sessionToken: str = Field(min_length=16)
    serviceId: str
    quantity: int = Field(default=1, ge=1, le=20)
    note: str = Field(default="", max_length=500)


class OrderEventRequest(BaseModel):
    status: str


class ConversationRequest(BaseModel):
    sessionToken: str = Field(min_length=16)


class MessageRequest(BaseModel):
    sessionToken: str = Field(min_length=16)
    originalText: str = Field(min_length=1, max_length=2000)
    sourceLocale: str = Field(default="en", min_length=2, max_length=10)
    targetLocale: str = Field(default="vi", min_length=2, max_length=10)


class StaffLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)


class StayLinkRequest(BaseModel):
    roomNumber: str = Field(min_length=1, max_length=20)
    locale: str = Field(default="en", min_length=2, max_length=10)
    expiresInMinutes: int = Field(default=60, ge=5, le=1440)


class StaffMessageRequest(BaseModel):
    originalText: str = Field(min_length=1, max_length=2000)
    sourceLocale: str = Field(default="vi", min_length=2, max_length=10)
    targetLocale: str = Field(default="en", min_length=2, max_length=10)


def order_dict(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "roomNumber": row["room_number"], "serviceId": row["service_id"], "status": row["status"], "quantity": row["quantity"], "note": row["note"], "dueAt": row["due_at"], "assignedRole": row["assigned_role"], "createdAt": row["created_at"], "updatedAt": row["updated_at"]}


def message_dict(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "conversationId": row["conversation_id"], "sender": row["sender"], "originalText": row["original_text"], "translatedText": row["translated_text"], "sourceLocale": row["source_locale"], "targetLocale": row["target_locale"], "createdAt": row["created_at"]}


def password_hash(password: str, salt: bytes | None = None) -> str:
    active_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), active_salt, 210_000)
    return f"{active_salt.hex()}${digest.hex()}"


def password_matches(password: str, encoded: str) -> bool:
    salt_hex, digest_hex = encoded.split("$", 1)
    return hmac.compare_digest(password_hash(password, bytes.fromhex(salt_hex)).split("$", 1)[1], digest_hex)


def bootstrap_staff(connection: sqlite3.Connection) -> None:
    email = os.getenv("HOTEL_BRIDGE_BOOTSTRAP_STAFF_EMAIL")
    password = os.getenv("HOTEL_BRIDGE_BOOTSTRAP_STAFF_PASSWORD")
    if not email or not password:
        return
    existing = connection.execute("SELECT id FROM staff_users WHERE email = ?", (email.lower(),)).fetchone()
    if not existing:
        connection.execute("INSERT INTO staff_users VALUES (?, ?, ?, ?, ?, ?)", ("STF-BOOTSTRAP", email.lower(), os.getenv("HOTEL_BRIDGE_BOOTSTRAP_STAFF_NAME", "Hotel Manager"), os.getenv("HOTEL_BRIDGE_BOOTSTRAP_STAFF_ROLE", "manager"), password_hash(password), now().isoformat()))


def require_staff(connection: sqlite3.Connection, authorization: str | None) -> sqlite3.Row:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "STAFF_AUTH_REQUIRED", "message": "Bearer token is required"})
    token_hash = hashlib.sha256(authorization.removeprefix("Bearer ").encode()).hexdigest()
    row = connection.execute("SELECT u.* FROM staff_tokens t JOIN staff_users u ON u.id = t.staff_id WHERE t.token_hash = ? AND t.expires_at > ?", (token_hash, now().isoformat())).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail={"code": "INVALID_STAFF_TOKEN", "message": "Staff token is missing or expired"})
    return row


def stay_link_secret() -> bytes:
    secret = os.getenv("HOTEL_BRIDGE_STAY_LINK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail={"code": "STAY_LINK_NOT_CONFIGURED", "message": "Stay-link signing is not configured"})
    return secret.encode()


def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def unb64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_stay_link_token(room_number: str, locale: str, expires_in_minutes: int) -> tuple[str, str]:
    expires_at = (now() + timedelta(minutes=expires_in_minutes)).isoformat()
    payload = {"roomNumber": room_number, "locale": locale, "expiresAt": expires_at, "nonce": secrets.token_urlsafe(12)}
    encoded = b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    signature = b64url(hmac.new(stay_link_secret(), encoded.encode(), hashlib.sha256).digest())
    return f"{encoded}.{signature}", expires_at


def verify_stay_link_token(token: str) -> dict:
    try:
        encoded, signature = token.split(".", 1)
        expected = b64url(hmac.new(stay_link_secret(), encoded.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        payload = json.loads(unb64url(encoded))
        if datetime.fromisoformat(payload["expiresAt"]) <= now():
            raise ValueError("expired")
        if not isinstance(payload["roomNumber"], str) or not isinstance(payload["locale"], str):
            raise ValueError("payload")
        return payload
    except (ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail={"code": "INVALID_STAY_LINK", "message": "Stay link is invalid or expired"})


def require_session(connection: sqlite3.Connection, token: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM guest_sessions WHERE token = ?", (token,)).fetchone()
    if not row or datetime.fromisoformat(row["expires_at"]) <= now():
        raise HTTPException(status_code=401, detail={"code": "INVALID_SESSION", "message": "Guest session is missing or expired"})
    return row


@app.post("/api/staff/login")
def staff_login(payload: StaffLoginRequest) -> dict:
    with db() as connection:
        staff = connection.execute("SELECT * FROM staff_users WHERE email = ?", (payload.email.lower(),)).fetchone()
        if not staff or not password_matches(payload.password, staff["password_hash"]):
            raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Email or password is incorrect"})
        token = secrets.token_urlsafe(32)
        expires_at = (now() + timedelta(hours=8)).isoformat()
        connection.execute("DELETE FROM staff_tokens WHERE expires_at <= ?", (now().isoformat(),))
        connection.execute("INSERT INTO staff_tokens VALUES (?, ?, ?, ?)", (hashlib.sha256(token.encode()).hexdigest(), staff["id"], expires_at, now().isoformat()))
        connection.execute("INSERT INTO audit_events(entity_type, entity_id, action, actor, created_at) VALUES (?, ?, ?, ?, ?)", ("staff", staff["id"], "login", staff["email"], now().isoformat()))
    return {"accessToken": token, "expiresAt": expires_at, "staff": {"id": staff["id"], "displayName": staff["display_name"], "role": staff["role"]}}


@app.get("/api/staff/me")
def staff_me(authorization: str | None = Header(default=None)) -> dict:
    with db() as connection:
        staff = require_staff(connection, authorization)
    return {"id": staff["id"], "email": staff["email"], "displayName": staff["display_name"], "role": staff["role"]}


@app.post("/api/staff/logout")
def staff_logout(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "STAFF_AUTH_REQUIRED", "message": "Bearer token is required"})
    token_hash = hashlib.sha256(authorization.removeprefix("Bearer ").encode()).hexdigest()
    with db() as connection:
        staff = require_staff(connection, authorization)
        connection.execute("DELETE FROM staff_tokens WHERE token_hash = ?", (token_hash,))
        connection.execute("INSERT INTO audit_events(entity_type, entity_id, action, actor, created_at) VALUES (?, ?, ?, ?, ?)", ("staff", staff["id"], "logout", staff["email"], now().isoformat()))
    return {"ok": True}


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, service="hotel-bridge-api", version="0.2.0")


@app.get("/api/services")
def services() -> dict:
    return {"services": SERVICES}


@app.post("/api/guest-sessions", status_code=201)
def create_guest_session(payload: SessionRequest) -> dict:
    token = secrets.token_urlsafe(24)
    created = now()
    expires = created + timedelta(hours=24)
    with db() as connection:
        connection.execute("INSERT INTO guest_sessions VALUES (?, ?, ?, ?, ?)", (token, payload.roomNumber, payload.locale, expires.isoformat(), created.isoformat()))
        connection.execute("INSERT INTO audit_events(entity_type, entity_id, action, actor, created_at) VALUES (?, ?, ?, ?, ?)", ("session", token, "created", "guest", created.isoformat()))
    return {"token": token, "roomNumber": payload.roomNumber, "locale": payload.locale, "expiresAt": expires.isoformat()}


@app.post("/api/stay-links", status_code=201)
def create_stay_link(payload: StayLinkRequest, authorization: str | None = Header(default=None)) -> dict:
    with db() as connection:
        staff = require_staff(connection, authorization)
        if staff["role"] not in ("manager", "front_desk"):
            raise HTTPException(status_code=403, detail={"code": "STAY_LINK_FORBIDDEN", "message": "Only front desk or manager can issue a stay link"})
        token, expires_at = create_stay_link_token(payload.roomNumber, payload.locale, payload.expiresInMinutes)
        connection.execute("INSERT INTO audit_events(entity_type, entity_id, action, actor, created_at) VALUES (?, ?, ?, ?, ?)", ("stay_link", payload.roomNumber, "issued", staff["email"], now().isoformat()))
    return {"stayLinkToken": token, "expiresAt": expires_at, "roomNumber": payload.roomNumber, "locale": payload.locale}


@app.post("/api/guest-sessions/from-stay-link", status_code=201)
def create_guest_session_from_stay_link(stayLinkToken: str = Query(min_length=20)) -> dict:
    payload = verify_stay_link_token(stayLinkToken)
    token = secrets.token_urlsafe(24)
    created = now()
    expires = min(created + timedelta(hours=24), datetime.fromisoformat(payload["expiresAt"]))
    with db() as connection:
        connection.execute("INSERT INTO guest_sessions VALUES (?, ?, ?, ?, ?)", (token, payload["roomNumber"], payload["locale"], expires.isoformat(), created.isoformat()))
        connection.execute("INSERT INTO audit_events(entity_type, entity_id, action, actor, created_at) VALUES (?, ?, ?, ?, ?)", ("session", token, "created_from_stay_link", "guest", created.isoformat()))
    return {"token": token, "roomNumber": payload["roomNumber"], "locale": payload["locale"], "expiresAt": expires.isoformat()}


@app.post("/api/orders", status_code=201)
def create_order(payload: OrderRequest) -> dict:
    with db() as connection:
        session = require_session(connection, payload.sessionToken)
        service = next((item for item in SERVICES if item["id"] == payload.serviceId), None)
        if not service:
            raise HTTPException(status_code=404, detail={"code": "SERVICE_NOT_FOUND", "message": "Service is not available"})
        created = now()
        due = created + timedelta(minutes=service["etaMinutes"])
        order_id = f"HB-{secrets.token_hex(3).upper()}"
        connection.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (order_id, session["room_number"], service["id"], payload.quantity, payload.note, "NEW", service["department"], due.isoformat(), created.isoformat(), created.isoformat(), payload.sessionToken))
        connection.execute("INSERT INTO audit_events(entity_type, entity_id, action, actor, created_at) VALUES (?, ?, ?, ?, ?)", ("order", order_id, "created", "guest", created.isoformat()))
        row = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return order_dict(row)


@app.get("/api/orders")
def list_orders(sessionToken: str | None = None, authorization: str | None = Header(default=None)) -> dict:
    with db() as connection:
        if sessionToken:
            session = require_session(connection, sessionToken)
            rows = connection.execute("SELECT * FROM orders WHERE session_token = ? ORDER BY created_at DESC", (session["token"],)).fetchall()
        else:
            role = require_staff(connection, authorization)["role"]
            if role == "manager" or role == "front_desk":
                rows = connection.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
            else:
                rows = connection.execute("SELECT * FROM orders WHERE assigned_role = ? ORDER BY created_at DESC", (role,)).fetchall()
    return {"orders": [order_dict(row) for row in rows]}


@app.post("/api/orders/{order_id}/events")
def update_order(order_id: str, payload: OrderEventRequest, authorization: str | None = Header(default=None)) -> dict:
    with db() as connection:
        staff = require_staff(connection, authorization)
        role = staff["role"]
        if payload.status not in STATUSES:
            raise HTTPException(status_code=422, detail={"code": "INVALID_STATUS", "message": "Unsupported order status"})
        row = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "Order does not exist"})
        if role not in ("manager", "front_desk") and role != row["assigned_role"]:
            raise HTTPException(status_code=403, detail={"code": "DEPARTMENT_FORBIDDEN", "message": "This order belongs to another department"})
        updated = now().isoformat()
        connection.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", (payload.status, updated, order_id))
        connection.execute("INSERT INTO audit_events(entity_type, entity_id, action, actor, created_at) VALUES (?, ?, ?, ?, ?)", ("order", order_id, f"status:{payload.status}", staff["email"], updated))
        changed = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return order_dict(changed)


@app.get("/api/management/inbox")
def management_inbox(authorization: str | None = Header(default=None)) -> dict:
    return list_orders(authorization=authorization)


@app.post("/api/conversations", status_code=201)
def create_conversation(payload: ConversationRequest) -> dict:
    with db() as connection:
        session = require_session(connection, payload.sessionToken)
        timestamp = now().isoformat()
        conversation_id = f"CB-{secrets.token_hex(4).upper()}"
        connection.execute("INSERT INTO conversations VALUES (?, ?, ?, ?, ?)", (conversation_id, session["token"], session["room_number"], timestamp, timestamp))
        connection.execute("INSERT INTO audit_events(entity_type, entity_id, action, actor, created_at) VALUES (?, ?, ?, ?, ?)", ("conversation", conversation_id, "created", "guest", timestamp))
    return {"id": conversation_id, "roomNumber": session["room_number"], "createdAt": timestamp, "updatedAt": timestamp}


@app.get("/api/conversations/{conversation_id}/messages")
def list_messages(conversation_id: str, sessionToken: str = Query(min_length=16)) -> dict:
    with db() as connection:
        session = require_session(connection, sessionToken)
        conversation = connection.execute("SELECT * FROM conversations WHERE id = ? AND session_token = ?", (conversation_id, session["token"])).fetchone()
        if not conversation:
            raise HTTPException(status_code=404, detail={"code": "CONVERSATION_NOT_FOUND", "message": "Conversation does not exist"})
        rows = connection.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,)).fetchall()
    return {"messages": [message_dict(row) for row in rows]}


@app.post("/api/conversations/{conversation_id}/messages", status_code=201)
def send_message(conversation_id: str, payload: MessageRequest) -> dict:
    with db() as connection:
        session = require_session(connection, payload.sessionToken)
        conversation = connection.execute("SELECT * FROM conversations WHERE id = ? AND session_token = ?", (conversation_id, session["token"])).fetchone()
        if not conversation:
            raise HTTPException(status_code=404, detail={"code": "CONVERSATION_NOT_FOUND", "message": "Conversation does not exist"})
        timestamp = now().isoformat()
        message_id = f"MSG-{secrets.token_hex(4).upper()}"
        translated = payload.originalText if payload.sourceLocale == payload.targetLocale else f"[demo translation → {payload.targetLocale}] {payload.originalText}"
        connection.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (message_id, conversation_id, "guest", payload.originalText, translated, payload.sourceLocale, payload.targetLocale, timestamp))
        connection.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (timestamp, conversation_id))
        connection.execute("INSERT INTO audit_events(entity_type, entity_id, action, actor, created_at) VALUES (?, ?, ?, ?, ?)", ("message", message_id, "created", "guest", timestamp))
        row = connection.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return message_dict(row)


@app.get("/api/management/conversations")
def management_conversations(authorization: str | None = Header(default=None)) -> dict:
    with db() as connection:
        require_staff(connection, authorization)
        rows = connection.execute("SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count FROM conversations c ORDER BY c.updated_at DESC").fetchall()
    return {"conversations": [{"id": row["id"], "roomNumber": row["room_number"], "messageCount": row["message_count"], "createdAt": row["created_at"], "updatedAt": row["updated_at"]} for row in rows]}


@app.get("/api/management/conversations/{conversation_id}/messages")
def management_messages(conversation_id: str, authorization: str | None = Header(default=None)) -> dict:
    with db() as connection:
        require_staff(connection, authorization)
        conversation = connection.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        if not conversation:
            raise HTTPException(status_code=404, detail={"code": "CONVERSATION_NOT_FOUND", "message": "Conversation does not exist"})
        rows = connection.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,)).fetchall()
    return {"messages": [message_dict(row) for row in rows]}


@app.post("/api/management/conversations/{conversation_id}/messages", status_code=201)
def management_send_message(conversation_id: str, payload: StaffMessageRequest, authorization: str | None = Header(default=None)) -> dict:
    with db() as connection:
        staff = require_staff(connection, authorization)
        conversation = connection.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        if not conversation:
            raise HTTPException(status_code=404, detail={"code": "CONVERSATION_NOT_FOUND", "message": "Conversation does not exist"})
        timestamp = now().isoformat()
        message_id = f"MSG-{secrets.token_hex(4).upper()}"
        translated = payload.originalText if payload.sourceLocale == payload.targetLocale else f"[demo translation → {payload.targetLocale}] {payload.originalText}"
        connection.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (message_id, conversation_id, "staff", payload.originalText, translated, payload.sourceLocale, payload.targetLocale, timestamp))
        connection.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (timestamp, conversation_id))
        connection.execute("INSERT INTO audit_events(entity_type, entity_id, action, actor, created_at) VALUES (?, ?, ?, ?, ?)", ("message", message_id, f"created:{staff['role']}", staff["email"], timestamp))
        row = connection.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return message_dict(row)


@app.get("/api/audit")
def audit(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    with db() as connection:
        rows = connection.execute("SELECT entity_type AS entityType, entity_id AS entityId, action, actor, created_at AS createdAt FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return {"events": [dict(row) for row in rows]}
