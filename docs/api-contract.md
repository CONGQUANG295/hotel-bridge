# API Contract — Foundation

## System

- `GET /api/health` — service health.
- `GET /api/services` — active hotel service catalog.
- `GET /api/audit` — audit events for pilot inspection.

## Guest sessions and orders

- `POST /api/guest-sessions` — create a guest room session.
- `POST /api/orders` — create an order using a guest session token.
- `GET /api/orders?sessionToken=...` — guest-scoped order list.
- `GET /api/orders` — staff order list, scoped by the role resolved from a bearer token.
- `POST /api/orders/{id}/events` — staff-only order lifecycle update.
- `GET /api/management/inbox` — department-scoped staff queue.

## Staff authentication and stay links

- `POST /api/staff/login` — staff email/password login, returns an 8-hour bearer token.
- `GET /api/staff/me` — verify the active bearer token.
- `POST /api/staff/logout` — revoke the active bearer token.
- Staff operations routes require `Authorization: Bearer <token>`; the legacy `X-Staff-Role` header is no longer accepted.
- `POST /api/stay-links` — front desk/manager issues a short-lived signed QR/deep-link token for a room/stay.
- `POST /api/guest-sessions/from-stay-link?stayLinkToken=...` — verifies the signed token and creates a guest session.

Stay-link signing requires `HOTEL_BRIDGE_STAY_LINK_SECRET` only at runtime. The token includes a room, locale, expiry and nonce, then is HMAC-SHA256 signed. Mobile app consumes it through:

```text
hotelbridge://stay/<signed-token>
```

Manual `POST /api/guest-sessions` remains a pilot fallback only. Production QR/NFC/Wi-Fi entry must use signed stay links or PMS-issued credentials.

## Guest chat

- `POST /api/conversations` — create a conversation using a guest session token.
- `GET /api/conversations/{id}/messages?sessionToken=...` — read messages for the guest's conversation.
- `POST /api/conversations/{id}/messages` — persist a guest message with original and translated fields.

## Staff chat

- `GET /api/management/conversations` — list guest conversations for staff.
- `GET /api/management/conversations/{id}/messages` — read a conversation as staff.
- `POST /api/management/conversations/{id}/messages` — send a staff reply.

Management chat endpoints require the same staff bearer token and role enforcement as inbox/order routes.

Message responses preserve both forms:

```json
{
  "originalText": "I need two extra towels",
  "translatedText": "[demo translation → vi] I need two extra towels",
  "sourceLocale": "en",
  "targetLocale": "vi"
}
```

The current translation output is deliberately labelled demo translation. A real translation provider will be added behind the same contract later.

Authentication now uses stay-scoped guest session tokens and bearer-token staff identity. Production still needs managed identity, account lifecycle, rate limits and HTTPS-only deployment.
