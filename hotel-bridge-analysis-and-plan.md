# Hotel Bridge — Phân tích sản phẩm và kế hoạch phát triển

## 1. Mục tiêu

Xây dựng nền tảng giúp khách sạn giải quyết hai vấn đề chính:

1. Rào cản ngôn ngữ giữa khách và nhân viên.
2. Khách có thể gọi dịch vụ trực tiếp từ phòng mà không cần gọi lễ tân hoặc cài ứng dụng.

Định hướng sản phẩm: **QR/NFC/Wi-Fi → mở PWA ngay → chọn ngôn ngữ → chat/order → nhân viên xử lý trên dashboard**.

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

### Guest PWA

Khách truy cập bằng QR code trên thẻ phòng, trong phòng, TV, menu, thang máy hoặc qua Wi-Fi captive portal.

Tính năng MVP:
- Chọn ngôn ngữ.
- Xác định phòng bằng mã phiên/QR.
- Chat với khách sạn.
- Dịch hai chiều giữa ngôn ngữ khách và ngôn ngữ khách sạn.
- Danh sách dịch vụ và giá.
- Tạo order.
- Theo dõi trạng thái order.
- Xem thông tin khách sạn và hỗ trợ khẩn cấp.

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

Native app chỉ nên phát triển sau khi có khách quay lại thường xuyên hoặc khách sạn cần chương trình loyalty.

## 7. Kiến trúc đề xuất

```text
Guest PWA
  ├── Chat đa ngôn ngữ
  ├── Service catalog
  ├── Order tracking
  └── Room authentication
          │
          ▼
Backend API
  ├── Translation service
  ├── Order management
  ├── Notification service
  ├── PMS/POS integration
  └── Payment integration
          │
          ▼
Staff Dashboard
```

### Stack dự kiến

- Guest app: Next.js PWA hoặc React PWA.
- Staff dashboard: React/Next.js.
- Backend: Node.js/NestJS hoặc FastAPI.
- Database: PostgreSQL.
- Realtime: WebSocket hoặc Supabase Realtime.
- Translation: Google Cloud Translation, DeepL hoặc AI model.
- Payment: payment gateway theo thị trường.

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

### Giai đoạn 1 — UX prototype

Mục tiêu: kiểm tra trải nghiệm trước khi xây backend.

Công việc:
- Guest flow: QR → language → chat/order.
- Staff flow: incoming request → translate → assign → complete.
- Test trên điện thoại nhỏ.
- Kiểm tra nội dung dài ở nhiều ngôn ngữ.
- Test QR/NFC placement trong phòng.

Kết quả:
- Prototype tương tác.
- Bộ UI components.
- Acceptance criteria cho MVP.

### Giai đoạn 2 — MVP pilot

Mục tiêu: chạy thật tại một khách sạn với các dịch vụ cơ bản.

Công việc:
- Xây backend và database.
- Tạo room/session authentication.
- Realtime chat.
- Translation adapter.
- Service/order management.
- Staff dashboard có phân quyền.
- Web push/email notification.
- QR riêng theo phòng.
- Audit log.

Kết quả:
- PWA chạy production.
- Dashboard cho nhân viên.
- Báo cáo order và thời gian phản hồi.

### Giai đoạn 3 — Tích hợp vận hành

Mục tiêu: giảm thao tác nhập liệu thủ công.

Công việc:
- Tích hợp PMS để xác nhận phòng đang lưu trú.
- Tích hợp POS/room charge.
- Tích hợp WhatsApp/Zalo.
- Wi-Fi captive portal.
- Thanh toán online.
- Quản lý nhiều chi nhánh.

Kết quả:
- Order có thể charge trực tiếp vào phòng hoặc thanh toán online.
- Một dashboard quản lý nhiều bộ phận và cơ sở.

### Giai đoạn 4 — Tối ưu và mở rộng

Mục tiêu: tăng tỷ lệ sử dụng và doanh thu dịch vụ.

Công việc:
- Voice translation.
- AI đề xuất dịch vụ phù hợp.
- Loyalty và hồ sơ khách quay lại.
- Native app cho khách thường xuyên.
- Analytics về doanh thu, SLA và mức độ hài lòng.
- White-label theo thương hiệu khách sạn.

## 9. Tiêu chí thành công MVP

- Khách mở được dịch vụ trong dưới 10 giây sau khi quét QR.
- Không cần tải app hoặc tạo tài khoản dài.
- Nhân viên nhận được order trong vòng 5 giây.
- Khách xem được trạng thái order rõ ràng.
- Nhân viên có thể xem bản gốc và bản dịch.
- Tối thiểu 80% order pilot được xử lý mà không cần gọi điện.
- Có log để truy vết mọi order và tin nhắn.

## 10. Rủi ro và cách xử lý

- Dịch sai: hiển thị bản gốc, câu trả lời mẫu và cảnh báo nội dung nhạy cảm.
- QR bị chia sẻ: dùng token theo phiên lưu trú và xác thực nhẹ.
- Nhân viên bỏ sót order: notification, SLA timer và escalation.
- Khách không có mạng: cung cấp nút gọi lễ tân và thông tin tối thiểu offline.
- Quá nhiều tính năng: chỉ pilot với 8 dịch vụ ưu tiên.
- Tích hợp PMS phức tạp: MVP cho phép nhập/quản lý room session thủ công.

## 11. Trạng thái source hiện tại

Thư mục `source-codes/` chứa MVP prototype:

- `index.html`: giao diện guest PWA và staff dashboard demo.
- `styles.css`: giao diện responsive.
- `app.js`: chat dịch mô phỏng, tạo order, cập nhật trạng thái và state local.
- `manifest.webmanifest`: cấu hình PWA.
- `sw.js`: service worker cache cơ bản.
- `README.md`: hướng dẫn chạy và phạm vi prototype.

Prototype hiện chưa phải production system. Bước kế tiếp là thay local state bằng backend API, database, dịch thuật thật, authentication và realtime transport.
