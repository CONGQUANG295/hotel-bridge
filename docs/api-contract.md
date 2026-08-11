# API Contract — Foundation

## System

- `GET /api/health` — service health.
- `GET /api/services` — active hotel service catalog.
- `GET /api/audit` — audit events for pilot inspection.

## Guest sessions and orders

- `POST /api/guest-sessions` — create a guest room session.
- `POST /api/orders` — create an order using a guest session token.
- `GET /api/orders?sessionToken=...` — guest-scoped order list.
- `GET /api/orders` — staff order list, scoped by `X-Staff-Role` when provided.
- `POST /api/orders/{id}/events` — staff-only order lifecycle update.
- `GET /api/management/inbox` — department-scoped staff queue.

## Guest chat

- `POST /api/conversations` — create a conversation using a guest session token.
- `GET /api/conversations/{id}/messages?sessionToken=...` — read messages for the guest's conversation.
- `POST /api/conversations/{id}/messages` — persist a guest message with original and translated fields.

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

Authentication and domain handlers will be expanded per module. Routes currently validate stay-scoped guest tokens and use `X-Staff-Role` for the pilot staff workflow; production staff authentication will replace the demo header.
