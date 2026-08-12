# Hotel Bridge

Hotel Bridge là nền tảng dịch vụ khách sạn **không cần khách tải app**. Khách truy cập Guest PWA bằng QR/NFC/link ngắn, chọn ngôn ngữ, chat với khách sạn và gọi dịch vụ trực tiếp từ phòng. Nhân viên xử lý yêu cầu trên Management Dashboard.

> **Current stage:** pilot vertical slice. Guest session, service catalog, SQLite order persistence, live guest order tracking, persisted guest chat, staff inbox, role-scoped status updates và audit log đã hoạt động. Bản dịch hiện là demo adapter có gắn nhãn; PMS, POS, translation provider thật và realtime notification chưa tích hợp.

## Architecture

```text
Guest Web / PWA ──┐
                  ├── FastAPI ── SQLite (pilot)
Management Web ───┘
```

Repository layout:

```text
apps/
  guest-web/          Guest-facing Next.js web app
  management-web/    Staff operations dashboard
  guest-mobile/      Expo mobile foundation for future use
services/api/        FastAPI backend
packages/
  shared-types/      Shared TypeScript domain types
  ui/                Shared UI package
  i18n/              Shared language package
docs/                API contract and architecture notes
prototype/v3-legacy/ Previous HTML prototype, kept for reference
```

## Requirements

- Node.js >= 22
- npm
- Python >= 3.13
- [`uv`](https://docs.astral.sh/uv/)

## Install

```bash
npm install
uv venv .venv
uv pip install --python .venv/bin/python -r services/api/requirements.txt
```

## Run locally

Start the API:

```bash
HOTEL_BRIDGE_DB=/tmp/hotel-bridge.db \
  .venv/bin/uvicorn services.api.app.main:app --reload --port 8000
```

Start the guest web app in another terminal:

```bash
npm run dev:guest
```

Start the staff dashboard in another terminal:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev:management
```

For the Expo mobile app:

```bash
npm --workspace apps/guest-mobile run start
```

Set the API URL for a physical device or a different emulator when needed:

```bash
EXPO_PUBLIC_API_URL=http://<YOUR-LAN-IP>:8000 npm --workspace apps/guest-mobile run start
```

The Android emulator default is `http://10.0.2.2:8000`. The iOS simulator normally uses `http://127.0.0.1:8000`.

Mobile validation commands:

```bash
npm --workspace apps/guest-mobile run typecheck
npm --workspace apps/guest-mobile run export:ios
npm --workspace apps/guest-mobile run export:android
```

The Expo app currently implements the mobile guest vertical slice: room session, service catalog, order creation and live order tracking. The exports validate iOS/Android JavaScript bundles; they are not signed IPA/AAB store files. App Store/Google Play submission still requires Expo EAS credentials, signing, store metadata, privacy policy and real-device QA.

The API creates the SQLite schema automatically. Runtime databases, `.env` files, caches and generated TypeScript build state are ignored by Git.

## API vertical slice

### Guest

Create a room session:

```bash
curl -X POST http://localhost:8000/api/guest-sessions \
  -H 'Content-Type: application/json' \
  -d '{"roomNumber":"302","locale":"vi"}'
```

Create an order using the returned token:

```bash
curl -X POST http://localhost:8000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"sessionToken":"<SESSION_TOKEN>","serviceId":"towels","quantity":2}'
```

List the guest's orders:

```bash
curl 'http://localhost:8000/api/orders?sessionToken=<SESSION_TOKEN>'
```

### Staff

List the operations inbox:

```bash
curl http://localhost:8000/api/management/inbox \
  -H 'X-Staff-Role: front_desk'
```

Update an order status:

```bash
curl -X POST http://localhost:8000/api/orders/<ORDER_ID>/events \
  -H 'Content-Type: application/json' \
  -H 'X-Staff-Role: housekeeping' \
  -d '{"status":"IN_PROGRESS"}'
```

Supported statuses:

```text
NEW · ACCEPTED · IN_PROGRESS · READY · DELIVERED · COMPLETED · CANCELLED · ESCALATED
```

Available staff roles:

```text
front_desk · housekeeping · restaurant · maintenance · manager
```

Audit events are available at `GET /api/audit`.

## Verification

```bash
python3 -m compileall -q services/api/app
npm run typecheck
npm run build
```

The API smoke flow should cover: session creation, authenticated order creation, guest order listing, department authorization (`403`), valid status update and audit event creation.

## Product roadmap

1. **Discovery:** validate hotel services, departments, supported languages and SLAs with a pilot hotel.
2. **UX prototype:** validate QR → language → chat/order → status on mobile screens.
3. **MVP pilot:** connect real translation, realtime chat, QR-per-room sessions, notifications and staff authentication.
4. **Operations integration:** PMS, POS/room charge, WhatsApp/Zalo, captive portal and online payment.
5. **Scale:** multi-property, analytics, voice translation, loyalty and optional native apps.

See [`docs/architecture.md`](docs/architecture.md), [`docs/api-contract.md`](docs/api-contract.md) and the legacy [`prototype/v3-legacy/hotel-bridge-analysis-and-plan.md`](prototype/v3-legacy/hotel-bridge-analysis-and-plan.md) for more detail.
