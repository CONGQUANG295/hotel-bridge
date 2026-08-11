# Hotel Bridge V3 — Pilot API Integration

Prototype giao diện cho nền tảng khách sạn gồm Guest PWA và Staff Dashboard.

## Chạy local

Không cần cài npm dependency. Từ thư mục `source-codes` chạy:

```bash
python3 -m http.server 4173
```

Mở `http://localhost:4173` trên trình duyệt.

> Service Worker chỉ hoạt động qua HTTP/HTTPS, không hoạt động đầy đủ khi mở trực tiếp bằng `file://`.

## Đã có trong prototype

- Guest experience responsive.
- Chat song ngữ mô phỏng English ↔ Vietnamese.
- Câu trả lời nhanh cho extra towels, breakfast và room issue.
- Danh sách 8 dịch vụ khách sạn.
- Tạo order và theo dõi trạng thái.
- Staff dashboard với inbox, thống kê và flow dịch vụ.
- State demo lưu trong `localStorage`.
- PWA manifest và service worker cache cơ bản.

## Chưa phải production

- Chưa có backend/database thật.
- Chưa kết nối translation API.
- Chưa có authentication/QR token thật.
- Chưa có WebSocket/realtime thật.
- Chưa có PMS/POS/payment integration.
- Chưa có push notification thật.

## Hướng phát triển tiếp theo

1. Chốt service catalog và quy trình tại khách sạn pilot.
2. Tách frontend thành Next.js PWA và staff dashboard.
3. Xây API + PostgreSQL cho rooms, stays, conversations, messages, services và orders.
4. Thay translation mock bằng translation adapter có fallback.
5. Thêm QR session token, staff roles, audit log.
6. Tích hợp realtime, notification và PMS/POS.

## V2 khác bản MVP cũ ở đâu?

- Giữ nguyên bản MVP tại `/opt/data/source-codes`.
- V2 nằm riêng tại `/opt/data/source-codes-v2`.
- Thêm onboarding 3 bước: room number → ngôn ngữ → chọn hành động.
- Hero flow tập trung vào thông điệp không cần tải app.
- Có trust signals: No download, No long sign-up, Human support.
- Có shortcut sau onboarding vào chat hoặc request service.
- Vẫn giữ staff dashboard, service catalog, order tracking và chat demo của MVP.

## V3 — pilot API integration

- Giữ nguyên V2 tại `/opt/data/source-codes-v2`.
- Backend stdlib-only tại `server.py`, không cần cài package.
- API health: `GET /api/health`.
- Service catalog: `GET /api/services`.
- Room orders: `GET /api/orders?room=302` và `POST /api/orders`.
- Room messages: `GET /api/messages?room=302` và `POST /api/messages`.
- State pilot được lưu ở `pilot-state.json`.
- Frontend tự hydrate từ API, fallback về local demo nếu API không khả dụng.
- Room session token được tạo khi khách mở app và lưu ở `sessionStorage`.
- `POST /api/orders` và `POST /api/messages` yêu cầu header `X-Room-Token` hợp lệ.
- Audit log ghi session, order và message events; xem bằng `GET /api/audit`.
- Storage pilot dùng SQLite tại `hotel-bridge.db`; file `pilot-state.json` chỉ giữ làm backup/migration.
- Khi database rỗng, dữ liệu legacy được migrate tự động từ JSON sang SQLite.
- Staff auth: `POST /api/staff/login`, `GET /api/staff/me`, `GET /api/staff/inbox`.
- Các role pilot: `front_desk`, `housekeeping`, `restaurant`, `maintenance`, `manager`.
- Tài khoản demo local: `linh`, `mina`, `alex`; password chung `bridge-demo`.
- `front_desk` và `manager` thấy toàn bộ inbox; các bộ phận khác chỉ thấy order thuộc bộ phận của mình.

## Chạy V3

```bash
cd /opt/data/source-codes-v3
python3 server.py
```

Mở `http://127.0.0.1:4175`. Server vừa phục vụ frontend vừa phục vụ API.
