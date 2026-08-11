from __future__ import annotations

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
    """)
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


def order_dict(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "roomNumber": row["room_number"], "serviceId": row["service_id"], "status": row["status"], "quantity": row["quantity"], "note": row["note"], "dueAt": row["due_at"], "assignedRole": row["assigned_role"], "createdAt": row["created_at"], "updatedAt": row["updated_at"]}


def require_session(connection: sqlite3.Connection, token: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM guest_sessions WHERE token = ?", (token,)).fetchone()
    if not row or datetime.fromisoformat(row["expires_at"]) <= now():
        raise HTTPException(status_code=401, detail={"code": "INVALID_SESSION", "message": "Guest session is missing or expired"})
    return row


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
def list_orders(sessionToken: str | None = Query(default=None), x_staff_role: Role | None = Header(default=None)) -> dict:
    with db() as connection:
        if sessionToken:
            session = require_session(connection, sessionToken)
            rows = connection.execute("SELECT * FROM orders WHERE session_token = ? ORDER BY created_at DESC", (session["token"],)).fetchall()
        else:
            role = x_staff_role or "front_desk"
            if role == "manager" or role == "front_desk":
                rows = connection.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
            else:
                rows = connection.execute("SELECT * FROM orders WHERE assigned_role = ? ORDER BY created_at DESC", (role,)).fetchall()
    return {"orders": [order_dict(row) for row in rows]}


@app.post("/api/orders/{order_id}/events")
def update_order(order_id: str, payload: OrderEventRequest, x_staff_role: Role | None = Header(default=None)) -> dict:
    if not x_staff_role:
        raise HTTPException(status_code=401, detail={"code": "STAFF_AUTH_REQUIRED", "message": "Staff role header is required"})
    if payload.status not in STATUSES:
        raise HTTPException(status_code=422, detail={"code": "INVALID_STATUS", "message": "Unsupported order status"})
    with db() as connection:
        row = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "Order does not exist"})
        if x_staff_role not in ("manager", "front_desk") and x_staff_role != row["assigned_role"]:
            raise HTTPException(status_code=403, detail={"code": "DEPARTMENT_FORBIDDEN", "message": "This order belongs to another department"})
        updated = now().isoformat()
        connection.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", (payload.status, updated, order_id))
        connection.execute("INSERT INTO audit_events(entity_type, entity_id, action, actor, created_at) VALUES (?, ?, ?, ?, ?)", ("order", order_id, f"status:{payload.status}", x_staff_role, updated))
        changed = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return order_dict(changed)


@app.get("/api/management/inbox")
def management_inbox(x_staff_role: Role | None = Header(default=None)) -> dict:
    return list_orders(x_staff_role=x_staff_role)


@app.get("/api/audit")
def audit(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    with db() as connection:
        rows = connection.execute("SELECT entity_type AS entityType, entity_id AS entityId, action, actor, created_at AS createdAt FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return {"events": [dict(row) for row in rows]}
