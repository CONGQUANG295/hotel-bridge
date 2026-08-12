# Hotel Bridge Architecture

Hotel Bridge có ba client dùng chung một FastAPI API:

```text
Guest Mobile App iOS/Android ─┐
Guest Web / PWA ──────────────┼── FastAPI ── SQLite (pilot) / PostgreSQL (production)
Management Web ───────────────┘
```

- **Guest Mobile App:** Expo/React Native, production target cho App Store và Google Play.
- **Guest PWA:** no-download channel cho khách vào bằng QR/NFC/Wi-Fi.
- **Management Web:** staff operations dashboard.

`prototype/v3-legacy` chỉ là reference frozen. Business logic mới nằm trong `services/api/app/`; các client dùng contract từ `packages/shared-types`.
