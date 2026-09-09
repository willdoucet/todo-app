## Celery

### Background jobs
- Every task is idempotent: redelivery after a worker crash produces the same end state.
- Tasks receive ids, not ORM objects, and re-fetch inside the task.
- Async DB from a task: a fresh event loop per invocation, engine disposed before the loop closes ("Future attached to a different loop" is the symptom of skipping this).
- Retries set `max_retries` and a backoff; a poison message cannot loop forever.
- Enqueue happens after the surrounding DB transaction commits, never inside it.
- Beat entries derive from `conf.beat_schedule`; the persistent schedule file is on a writable path (`--schedule=/tmp/...`) so non-root containers do not crash in `setup_schedule()`.

### Secrets & config
- A `rediss://` broker URL requires `broker_use_ssl` and `redis_backend_use_ssl` with `ssl_cert_reqs`; a plain `redis://` URL must not set them. Gate the SSL config on the URL scheme so one config boots locally and in production.
- `CERT_REQUIRED` against the system CA bundle; `CERT_NONE` only with a written reason.

### Operations
- Worker and beat are separate processes; exactly one beat instance runs anywhere.
- Task failures log the task id and arguments (never secrets) and are visible in the worker log.
- Sync intervals and sweep schedules are documented in BACKEND_STRUCTURE.md → Background Job Pattern.

### Testing
- Tests call the task function directly or run eagerly; nothing outside `integration/` depends on a live broker.
