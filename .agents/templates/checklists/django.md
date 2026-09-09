## Django

### Data & migrations
- Migrations are committed with the model change; `makemigrations --check` runs in CI.
- `RunPython` migrations have a reverse function and use historical models (`apps.get_model`), never imported models.
- Deletion behavior (`on_delete`) is deliberate on every FK.

### API & trust boundaries
- CSRF protection is on for session-authenticated POSTs; DRF permission classes are explicit per view (no implicit `AllowAny`).
- `ALLOWED_HOSTS`, `SECURE_*`, and `DEBUG=False` are set for production; `SECRET_KEY` has no default there.
- Querysets are scoped to the requesting user or tenant wherever more than one exists.

### Query efficiency
- List views use `select_related` / `prefetch_related` for what the serializer touches; hot paths have `assertNumQueries`.

### Background jobs
- Tasks receive ids; enqueueing happens in `transaction.on_commit`.

### Testing
- `TestCase` for database tests; factories over fixtures; the test database is separate.

### Secrets & config
- All settings come from env through one settings module; nothing secret is committed.
