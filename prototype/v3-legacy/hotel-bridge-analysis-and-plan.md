# Hotel Bridge — Phân tích sản phẩm và kế hoạch phát triển

## 1. Mục tiêu

Xây dựng nền tảng giúp khách sạn giải quyết hai vấn đề chính:

1. Rào cản ngôn ngữ giữa khách và nhân viên.
2. Khách có thể gọi dịch vụ trực tiếp từ phòng mà không cần gọi lễ tân hoặc cài ứng dụng.

Định hướng sản phẩm gồm hai kênh khách hàng dùng chung backend:

- **Guest Mobile App iOS/Android:** app production cho khách quay lại, loyalty và phân phối qua App Store/Google Play.
- **Guest PWA:** kênh no-download cho khách ngắn ngày qua QR/NFC/Wi-Fi/link ngắn.

Cả hai kênh dùng chung session, chat, service catalog, order và tracking; nhân viên xử lý trên Staff Dashboard.

## 2. Đối tượng sử dụng

### Khách lưu trú
- Khách quốc tế không nói tiếng Việt.
- Khách không muốn tải thêm app.
- Khách cần gọi dịch vụ nhanh trong phòng.

### Nhân viên khách sạn
- Lễ tân.
- Housekeeping.
- Nhà hàng/room service.
- Kỹ thuật/bảo trì.
- Quản lý.

## 3. Sản phẩm đề xuất

## Guest Mobile App iOS/Android

App production dùng Expo/React Native, dành cho khách quay lại và phân phối qua App Store/Google Play.

MVP:
- Room/session onboarding.
- Chọn ngôn ngữ.
- Service catalog.
- Tạo và theo dõi order.
- Chat đa ngôn ngữ.
- Loading, empty, offline và error states.
- Deep link từ QR/link ngắn.

## Guest PWA

Khách truy cập bằng QR code trên thẻ phòng, trong phòng, TV, menu, thang máy hoặc qua Wi-Fi captive portal. PWA phục vụ khách không muốn tải app và dùng chung API contract với Mobile App.

MVP:
- Chọn ngôn ngữ.
- Xác định phòng bằng mã phiên/QR.
- Chat với khách sạn.
- Dịch hai chiều.
- Danh sách dịch vụ và giá.
- Tạo order.
- Theo dõi trạng thái order.
- Hỗ trợ khẩn cấp.

### Staff Dashboard

Tính năng MVP:
- Xem các cuộc chat mới.
- Xem nội dung gốc và nội dung đã dịch.
- Trả lời bằng ngôn ngữ của khách sạn.
- Nhận order mới.
- Gán order cho bộ phận.
- Cập nhật trạng thái: đã gửi, đã tiếp nhận, đang xử lý, đang giao, hoàn tất.
- Quản lý câu trả lời mẫu.

## 4. Luồng trải nghiệm chính

### Luồng không cần cài app

1. Khách quét QR hoặc chạm NFC.
2. PWA mở trong trình duyệt.
3. Khách chọn ngôn ngữ.
4. Hệ thống xác thực bằng QR token/mã phòng/OTP.
5. Khách chọn Chat hoặc Đặt dịch vụ.
6. Nhân viên nhận yêu cầu trong dashboard.
7. Khách xem được trạng thái xử lý theo thời gian thực.

### Luồng chat dịch

1. Khách nhập tin nhắn.
2. Hệ thống phát hiện ngôn ngữ.
3. Hiển thị bản gốc và bản dịch cho nhân viên.
4. Nhân viên trả lời bằng ngôn ngữ của khách sạn.
5. Hệ thống dịch lại cho khách.
6. Các nội dung nhạy cảm như y tế, dị ứng, an ninh hoặc khiếu nại được gắn cảnh báo để nhân viên kiểm tra.

### Luồng order

1. Khách chọn dịch vụ.
2. Chọn số lượng và ghi chú.
3. Xác nhận order.
4. Hệ thống tạo mã order và định tuyến theo bộ phận.
5. Nhân viên cập nhật trạng thái.
6. Khách nhận thông báo khi order hoàn tất.

## 5. Dịch vụ nên có trong MVP

- Room service.
- Dọn phòng.
- Thay khăn.
- Thêm nước uống.
- Giặt ủi.
- Đặt taxi.
- Báo hỏng thiết bị.
- Late check-out.

## 6. Chiến lược tiếp cận khách chưa tải app

Ưu tiên theo thứ tự:

1. QR code tại quầy lễ tân, thẻ khóa phòng, trong phòng và menu.
2. NFC cạnh giường, điện thoại bàn hoặc TV.
3. Wi-Fi captive portal sau khi khách kết nối Wi-Fi.
4. Link ngắn trên TV hoặc card trong phòng.
5. Nút fallback sang WhatsApp/Zalo.
6. Cho phép khách thêm PWA vào Home Screen, nhưng không bắt buộc.

Mobile app là production target cho khách quay lại và loyalty; PWA vẫn là kênh no-download bắt buộc cho khách ngắn ngày.

## 7. Kiến trúc đề xuất

```text
Guest Mobile App iOS/Android ─┐
Guest PWA ─────────────────────┼── Backend API ── Database
Staff Dashboard ──────────────┘
```

Mobile App và Guest PWA dùng chung API contract; PWA là no-download acquisition channel, Mobile App là store-distributed product.

### Stack dự kiến

- Guest app: Expo/React Native + TypeScript, targeting iOS and Android stores.
- Guest PWA: Next.js/React, no-download channel.
- Staff dashboard: React/Next.js.
- Backend: FastAPI.
- Pilot database: SQLite; production target: PostgreSQL.
- Realtime: WebSocket/SSE after pilot; polling is acceptable for current MVP.
- Translation: provider adapter; current implementation uses labelled demo adapter.
- Payment: payment gateway theo thị trường.
- Distribution: Expo EAS for preview, signed production builds and store submission.

MVP prototype hiện tại dùng HTML/CSS/JavaScript thuần để chạy ngay không cần cài dependency. Đây là bản UX prototype có state local, chưa kết nối backend production.

## 8. Kế hoạch phát triển theo giai đoạn

### Giai đoạn 0 — Discovery và validation

Mục tiêu: xác nhận nhu cầu thực tế tại một khách sạn pilot.

Công việc:
- Chọn khách sạn pilot.
- Liệt kê dịch vụ và quy trình xử lý hiện tại.
- Xác định ngôn ngữ khách phổ biến.
- Xác định PMS/POS đang dùng.
- Phỏng vấn lễ tân, housekeeping và quản lý.
- Chốt SLA cho từng loại order.

Kết quả:
- Service catalog chuẩn.
- Ma trận bộ phận xử lý.
- Danh sách ngôn ngữ ưu tiên.
- Quy trình escalation.

### Giai đoạn 1 — UX prototype đa kênh

Mục tiêu: kiểm tra cùng một journey trên PWA và Mobile App.

Công việc:
- PWA: QR/NFC/Wi-Fi → room context → language → chat/order → status.
- Mobile: app launch/deep link → room/session → service → order → status.
- Staff: incoming request → translate → assign → complete.
- Test trên iPhone/Android screen nhỏ.
- Kiểm tra nội dung dài ở nhiều ngôn ngữ.
- Test QR/NFC placement và deep link.

Kết quả:
- PWA prototype tương tác.
- Mobile Expo prototype chạy được.
- Bộ UI components.
- Acceptance criteria cho MVP.

### Giai đoạn 2 — MVP pilot backend + mobile

Mục tiêu: có một vertical slice dùng được trên PWA, Mobile App và Staff Dashboard.

Công việc:
- Xây backend và database.
- Tạo room/session authentication.
- Service/order management.
- Guest chat và Staff chat.
- Translation adapter có nhãn demo khi chưa có provider thật.
- Staff dashboard có phân quyền.
- Mobile app có room onboarding, service catalog, order tracking và chat.
- PWA dùng chung API contract.
- Audit log.
- API smoke, browser check và iOS/Android bundle export.

Kết quả:
- Pilot backend chạy SQLite.
- PWA chạy được flow guest.
- Mobile app có Expo vertical slice.
- Dashboard cho nhân viên.

### Giai đoạn 3 — Hardening và store preparation

Mục tiêu: đưa mobile từ bundle demo lên preview build có thể cài trên thiết bị.

Công việc:
- PostgreSQL migration path.
- Staff login/bearer auth.
- QR/stay-scoped session issuance.
- Push notification/realtime transport.
- Mobile offline/error/retry states.
- Mobile deep links và persisted session.
- App icon, splash, privacy/support URLs.
- EAS project, development/preview build.
- QA trên iPhone thật và Android thật.

Kết quả:
- Preview build cài được qua TestFlight/internal distribution.
- Pilot security and persistence checks pass.

### Giai đoạn 4 — Store release và tích hợp vận hành

Mục tiêu: phát hành app và giảm thao tác vận hành thủ công.

Công việc:
- Signed iOS/TestFlight build.
- Signed Android AAB/internal testing.
- App Store Connect và Google Play metadata.
- PMS xác nhận phòng đang lưu trú.
- POS/room charge hoặc payment.
- WhatsApp/Zalo.
- Wi-Fi captive portal.
- Quản lý nhiều chi nhánh.

Kết quả:
- App có thể submit store.
- Order có thể charge trực tiếp hoặc thanh toán online.
- Dashboard quản lý nhiều bộ phận/cơ sở.

### Giai đoạn 5 — Tối ưu và mở rộng

Mục tiêu: tăng tỷ lệ sử dụng và doanh thu dịch vụ.

Công việc:
- Voice translation.
- AI đề xuất dịch vụ.
- Loyalty và hồ sơ khách quay lại.
- Analytics doanh thu, SLA và hài lòng.
- White-label.
- Multi-property tenancy.

## 9. Tiêu chí thành công MVP

- Guest mở được dịch vụ trong dưới 10 giây sau khi quét QR hoặc mở app.
- Mobile preview build cài được trên tối thiểu một iPhone và một Android.
- Không cần tải app hoặc tạo tài khoản dài khi dùng PWA.
- Nhân viên nhận được order trong vòng 5 giây.
- Khách xem được trạng thái order rõ ràng trên PWA và Mobile App.
- Nhân viên có thể xem bản gốc và bản dịch.
- Tối thiểu 80% order pilot được xử lý mà không cần gọi điện.
- Có log để truy vết mọi order và tin nhắn.
- Signed IPA/AAB chỉ được đánh dấu đạt sau khi build bằng credentials thật; bundle export không thay thế store build.

## 10. Rủi ro và cách xử lý

- Dịch sai: hiển thị bản gốc, câu trả lời mẫu và cảnh báo nội dung nhạy cảm.
- QR bị chia sẻ: dùng token theo phiên lưu trú và xác thực nhẹ.
- Nhân viên bỏ sót order: notification, SLA timer và escalation.
- Khách không có mạng: cung cấp nút gọi lễ tân và thông tin tối thiểu offline.
- Quá nhiều tính năng: chỉ pilot với 8 dịch vụ ưu tiên.
- Tích hợp PMS phức tạp: MVP cho phép nhập/quản lý room session thủ công.

## 11. Trạng thái source hiện tại

Canonical source là thư mục `/opt/data/source-codes-v3`.

- `apps/guest-mobile/`: Expo/React Native mobile app cho iOS/Android; đã có room session, service catalog, order creation, tracking và iOS/Android bundle export.
- `apps/guest-web/`: Guest PWA đã kết nối API thật cho session, service, order, tracking và chat.
- `apps/management-web/`: Staff Dashboard có order inbox, status update, conversation inbox và staff reply.
- `services/api/`: FastAPI pilot backend với SQLite, session token, order, chat và audit.
- `packages/shared-types/`: shared TypeScript contracts.
- `prototype/v3-legacy/`: prototype cũ, giữ làm reference.

Trạng thái phát hành mobile:

- Expo config resolve: **đã pass**.
- iOS JavaScript bundle export: **đã pass**.
- Android JavaScript bundle export: **đã pass**.
- Signed IPA/AAB: **chưa có**.
- Physical device QA: **chưa verify**.
- App Store/Google Play submission: **chưa thực hiện**.

Bước tiếp theo là hoàn thiện Mobile App MVP: chat mobile, session persistence/deep link, offline/error/retry states, app assets, EAS preview build và device QA. Không bắt đầu PMS/POS/payment trước khi Mobile/PWA pilot journey ổn định.
