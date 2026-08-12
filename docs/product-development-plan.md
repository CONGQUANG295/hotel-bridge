# Hotel Bridge — Product Development Plan

## Product direction

Hotel Bridge is a hospitality service platform with one backend and three clients:

```text
Guest Mobile App iOS/Android ─┐
Guest PWA (QR/NFC/Wi-Fi) ─────┼── FastAPI API ── Database
Staff Operations Web ─────────┘
```

- **Guest Mobile App:** production app for returning guests, loyalty and App Store/Google Play distribution.
- **Guest PWA:** no-download path for transient guests.
- **Staff Operations Web:** order, chat, department, SLA and audit operations.

Mobile and PWA share API contracts and business behavior. The PWA is not a replacement for the mobile app; it is the acquisition channel for guests who should not be forced to install anything.

## Current status

The canonical source is `/opt/data/source-codes-v3`. The project is between **Phase B — backend pilot hardening** and **Phase C — mobile app MVP**.

### Completed

- Guest room/session token.
- Service catalog API.
- Persistent SQLite orders.
- Guest order tracking.
- Staff inbox and department-scoped status updates.
- Audit events.
- Guest chat persistence.
- Staff chat inbox and reply.
- Guest PWA real API flow.
- Expo mobile flow: room/session → services → order → tracking → chat.
- iOS/Android bundle export.

### Not completed

- Mobile session persistence and deep links.
- Offline/error/retry UX.
- Real staff authentication.
- QR/stay validation from PMS.
- Real translation provider.
- Push notifications/realtime transport.
- PostgreSQL production migration.
- Physical iPhone/Android QA.
- Signed IPA/AAB and store submission.
- Pilot hotel discovery and acceptance sign-off.

## Delivery phases

### Phase A — Pilot discovery

Confirm pilot hotel, services, department routing, languages, SLA, escalation, PMS/POS, charge policy, privacy and data retention.

**Exit gate:** written pilot acceptance criteria.

### Phase B — Backend pilot hardening

Add stable API contract, PostgreSQL migration path, real staff bearer authentication, QR/stay-scoped session issuance, translation adapter, unread/notification strategy and security/retention tests.

**Exit gate:** API smoke, persistence-after-restart and authorization tests pass.

### Phase C — Mobile App MVP

Complete Expo app with room/session onboarding, services, orders, tracking, chat, persisted session, deep links, loading/empty/offline/error/retry states, icons/splash and device QA.

**Exit gate:** preview build installs on at least one iPhone and one Android device and completes session → order → status → chat.

### Phase D — PWA parity

Complete QR/NFC/Wi-Fi entry and ensure transient guests can use the same order/chat journey without installing the app.

**Exit gate:** no-download guest flow works end to end.

### Phase E — Store release

Configure EAS production builds, Apple/Google credentials, signed iOS/TestFlight build, signed Android AAB/internal track, store metadata, privacy/support URLs, screenshots, data safety and crash monitoring.

**Exit gate:** builds install through TestFlight and Google Play internal testing.

### Phase F — Pilot launch and integrations

Add PMS room validation, POS/room charge or payments, push notifications, escalation, real staff identity and pilot analytics.

### Phase G — Scale

Only after pilot evidence: multi-property, analytics, voice translation, loyalty, AI recommendations and white-label.

## Immediate coding order

1. Mobile chat using existing conversation API.
2. Mobile session persistence and QR/deep-link onboarding.
3. Mobile offline/error/retry handling.
4. App assets and store metadata.
5. EAS preview build.
6. Physical device QA.
7. Production authentication and staging environment.
8. Signed TestFlight/AAB builds.

Do not start PMS/POS/payment integrations before the mobile and PWA pilot journeys pass their exit gates.

## Release terminology

- iOS/Android bundle export: validates JavaScript bundling only.
- Preview build: installable test build, not production release.
- Signed IPA/AAB: required for store testing/release.
- Store submission: only after signed builds, metadata, privacy and QA are complete.
