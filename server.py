#!/usr/bin/env python3
"""Hotel Bridge V3 pilot API. Stdlib-only backend for local development."""
from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from storage import load_state, save_state

ROOT = Path(__file__).parent
STATE_FILE = ROOT / "pilot-state.json"

# Local pilot accounts only. Replace with env/SSO before production.
STAFF_USERS = {
    "linh": {"password": "bridge-demo", "display_name": "Linh Pham", "role": "front_desk", "department": "Guest experience"},
    "mina": {"password": "bridge-demo", "display_name": "Mina Tran", "role": "housekeeping", "department": "Housekeeping"},
    "alex": {"password": "bridge-demo", "display_name": "Alex Nguyen", "role": "manager", "department": "Management"},
}
STAFF_ROLES = {"front_desk", "housekeeping", "restaurant", "maintenance", "manager"}

SERVICES = [
    {"id": "towels", "icon": "▤", "name": "Extra towels", "vi": "Thêm khăn tắm", "price": "Complimentary", "eta": "10–15 min"},
    {"id": "water", "icon": "♧", "name": "Bottled water", "vi": "Nước đóng chai", "price": "Free", "eta": "5–10 min"},
    {"id": "room-service", "icon": "✣", "name": "Room service", "vi": "Đồ ăn tại phòng", "price": "From $8", "eta": "25–35 min"},
    {"id": "laundry", "icon": "⌁", "name": "Laundry service", "vi": "Dịch vụ giặt ủi", "price": "From $5", "eta": "Same day"},
    {"id": "housekeeping", "icon": "✧", "name": "Housekeeping", "vi": "Dọn phòng", "price": "Complimentary", "eta": "15–20 min"},
    {"id": "taxi", "icon": "⌖", "name": "Book a taxi", "vi": "Đặt taxi", "price": "Metered", "eta": "5–10 min"},
    {"id": "maintenance", "icon": "⚒", "name": "Room maintenance", "vi": "Báo hỏng thiết bị", "price": "Complimentary", "eta": "10–20 min"},
    {"id": "checkout", "icon": "◷", "name": "Late check-out", "vi": "Trả phòng muộn", "price": "From $20", "eta": "Subject to availability"},
]

DEFAULT_STATE = {
    "orders": [
        {"id": "HB-1042", "room": "302", "service_id": "towels", "quantity": 2, "status": "In progress", "created_at": "Today, 10:42"},
        {"id": "HB-1038", "room": "302", "service_id": "water", "quantity": 2, "status": "Completed", "created_at": "Today, 09:18"},
    ],
    "messages": [
        {"id": "m-1", "room": "302", "mine": False, "name": "Linh", "original": "Xin chào! Tôi có thể giúp gì cho bạn hôm nay?", "translated": "Hello! How can I help you today?"},
        {"id": "m-2", "room": "302", "mine": True, "name": "You", "original": "Could I have two extra towels, please?", "translated": "Tôi có thể xin thêm hai chiếc khăn tắm được không?"},
        {"id": "m-3", "room": "302", "mine": False, "name": "Linh", "original": "Tất nhiên rồi. Nhân viên sẽ mang lên trong khoảng 10 phút.", "translated": "Of course. A team member will bring them up in about 10 minutes."},
    ],
    "sessions": [],
    "audit": [],
}


def now_label():
    return datetime.now(timezone.utc).astimezone().strftime("%d %b %H:%M")


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def create_session(state, room, language="en"):
    token = uuid.uuid4().hex + uuid.uuid4().hex[:8]
    session = {"token": token, "room": str(room), "language": language, "created_at": iso_now(), "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()}
    state.setdefault("sessions", []).append(session)
    return session


def validate_session(state, token, room):
    if not token:
        return None
    now = datetime.now(timezone.utc)
    for session in reversed(state.get("sessions", [])):
        if session["token"] == token and session["room"] == str(room):
            try:
                if datetime.fromisoformat(session["expires_at"]) > now:
                    return session
            except ValueError:
                return None
    return None


def audit(state, action, room, detail=""):
    state.setdefault("audit", []).append({"id": uuid.uuid4().hex[:10], "action": action, "room": str(room), "detail": detail, "created_at": iso_now()})
    state["audit"] = state["audit"][-500:]


def issue_staff_session(state, username, user):
    token = uuid.uuid4().hex + uuid.uuid4().hex[:8]
    session = {"token": token, "username": username, "role": user["role"], "created_at": iso_now(), "expires_at": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()}
    state.setdefault("staff_sessions", []).append(session)
    state["staff_sessions"] = state["staff_sessions"][-100:]
    return session


def current_staff(state, token):
    if not token:
        return None
    now = datetime.now(timezone.utc)
    for session in reversed(state.get("staff_sessions", [])):
        if session["token"] == token:
            try:
                if datetime.fromisoformat(session["expires_at"]) <= now:
                    return None
            except ValueError:
                return None
            user = STAFF_USERS.get(session["username"])
            if user:
                return {"username": session["username"], **user, "token": token}
    return None


def require_staff(handler, state, roles=None):
    token = handler.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    user = current_staff(state, token)
    if not user or (roles and user["role"] not in roles):
        handler.send_json({"error": "Staff authentication required"}, 401)
        return None
    return user


def translate_reply(text: str):
    lower = text.lower()
    if "breakfast" in lower:
        return "Bữa sáng được phục vụ từ 07:00 đến 10:30 tại Riverside Kitchen."
    if "air conditioning" in lower or "maintenance" in lower:
        return "Tôi đã báo bộ phận kỹ thuật. Nhân viên sẽ lên phòng trong khoảng 10 phút."
    if "towel" in lower:
        return "Tất nhiên rồi. Nhân viên sẽ mang thêm khăn lên trong khoảng 10 phút."
    return "Cảm ơn bạn. Đội ngũ của chúng tôi sẽ hỗ trợ bạn ngay."


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"{self.command} {self.path} - {fmt % args}")

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Room-Token, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self.send_json({"ok": True, "service": "hotel-bridge-pilot-api", "storage": "sqlite"})
        if parsed.path == "/api/services":
            return self.send_json({"services": SERVICES})
        if parsed.path == "/api/audit":
            state = load_state()
            if not require_staff(self, state, {"front_desk", "manager"}):
                return
            return self.send_json({"audit": state.get("audit", [])[-100:]})
        if parsed.path == "/api/staff/me":
            state = load_state()
            user = require_staff(self, state)
            if not user:
                return
            safe_user = {key: user[key] for key in ("username", "display_name", "role", "department")}
            return self.send_json({"user": safe_user})
        if parsed.path == "/api/staff/inbox":
            state = load_state()
            user = require_staff(self, state)
            if not user:
                return
            visible = state["orders"] if user["role"] in {"front_desk", "manager"} else [o for o in state["orders"] if (user["role"] == "housekeeping" and o["service_id"] in {"towels", "housekeeping"}) or (user["role"] == "maintenance" and o["service_id"] == "maintenance") or (user["role"] == "restaurant" and o["service_id"] == "room-service")]
            return self.send_json({"user": {"username": user["username"], "role": user["role"], "department": user["department"]}, "orders": visible, "open_count": sum(o["status"] != "Completed" for o in visible)})
        state = load_state()
        if parsed.path == "/api/orders":
            room = parse_qs(parsed.query).get("room", [None])[0]
            orders = [o for o in state["orders"] if not room or o["room"] == room]
            return self.send_json({"orders": orders})
        if parsed.path == "/api/messages":
            room = parse_qs(parsed.query).get("room", [None])[0]
            messages = [m for m in state["messages"] if not room or m["room"] == room]
            return self.send_json({"messages": messages})
        return self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self.read_json()
        except (json.JSONDecodeError, ValueError):
            return self.send_json({"error": "Invalid JSON"}, 400)
        state = load_state()
        if parsed.path == "/api/staff/login":
            username = str(data.get("username", "")).strip().lower()
            password = str(data.get("password", ""))
            user = STAFF_USERS.get(username)
            if not user or not hmac.compare_digest(password, user["password"]):
                return self.send_json({"error": "Invalid staff credentials"}, 401)
            session = issue_staff_session(state, username, user)
            audit(state, "staff.login", "-", username)
            save_state(state)
            return self.send_json({"token": session["token"], "expires_at": session["expires_at"], "user": {"username": username, "display_name": user["display_name"], "role": user["role"], "department": user["department"]}}, 201)
        if parsed.path == "/api/sessions":
            room = str(data.get("room", "")).strip()
            if not room or len(room) > 8:
                return self.send_json({"error": "A valid room number is required"}, 400)
            session = create_session(state, room, str(data.get("language", "en")))
            audit(state, "session.created", room, "guest room session issued")
            save_state(state)
            return self.send_json({"session": session}, 201)
        if parsed.path == "/api/orders":
            room = str(data.get("room", "302"))
            if not validate_session(state, self.headers.get("X-Room-Token"), room):
                return self.send_json({"error": "Valid room session token required"}, 401)
            service = next((s for s in SERVICES if s["id"] == data.get("service_id")), None)
            if not service:
                return self.send_json({"error": "Unknown service"}, 400)
            order = {"id": f"HB-{uuid.uuid4().hex[:6].upper()}", "room": str(data.get("room", "302")), "service_id": service["id"], "quantity": int(data.get("quantity", 1)), "status": "New request", "created_at": now_label()}
            state["orders"].insert(0, order)
            audit(state, "order.created", order["room"], order["id"])
            save_state(state)
            return self.send_json({"order": order}, 201)
        if parsed.path == "/api/messages":
            text = str(data.get("text", "")).strip()
            if not text:
                return self.send_json({"error": "Message cannot be empty"}, 400)
            room = str(data.get("room", "302"))
            if not validate_session(state, self.headers.get("X-Room-Token"), room):
                return self.send_json({"error": "Valid room session token required"}, 401)
            customer = {"id": f"m-{uuid.uuid4().hex[:8]}", "room": room, "mine": True, "name": "You", "original": text, "translated": "Đang dịch sang tiếng Việt…"}
            state["messages"].append(customer)
            reply = {"id": f"m-{uuid.uuid4().hex[:8]}", "room": room, "mine": False, "name": "Linh", "original": translate_reply(text), "translated": text}
            state["messages"].append(reply)
            audit(state, "message.created", room, customer["id"])
            save_state(state)
            return self.send_json({"messages": [customer, reply]}, 201)
        return self.send_json({"error": "Not found"}, 404)

    def serve_static(self, path):
        relative = path.lstrip("/") or "index.html"
        target = (ROOT / relative).resolve()
        if ROOT not in target.parents and target != ROOT:
            return self.send_json({"error": "Forbidden"}, 403)
        if not target.is_file():
            return self.send_json({"error": "Not found"}, 404)
        content = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    port = 4175
    print(f"Hotel Bridge pilot API running at http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
