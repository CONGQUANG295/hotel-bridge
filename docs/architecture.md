# Hotel Bridge Architecture

Hotel Bridge has three clients over one API:

```text
Guest Web/PWA ───────┐
Guest Native App ────┼── FastAPI API ─── PostgreSQL
Management Web ──────┘
```

`prototype/v3-legacy` is frozen reference code only. New business logic belongs in `services/api/app/<domain>` and clients consume API contracts through `packages/shared-types`.
