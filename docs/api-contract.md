# API Contract — Foundation

- `GET /api/health` — service health.
- `GET /api/services` — active hotel service catalog.
- `POST /api/guest-sessions` — create a guest room session.
- `POST /api/orders` — create an order using a guest session.
- `GET /api/orders` — guest or staff-scoped order list.
- `POST /api/orders/{id}/events` — append an order lifecycle event.
- `GET /api/management/inbox` — department-scoped staff queue.
- `POST /api/conversations/{id}/messages` — send a chat message.

Authentication and domain handlers will be added per module; routes must not access database tables directly.
