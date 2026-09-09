## PostgreSQL

### Data & migrations
- Every FK declares its delete behavior and the ERD shows it.
- Every business rule that Pydantic checks across fields also has a CHECK constraint.
- Uniqueness among soft-deleted rows uses a partial unique index.
- Timestamps are `timestamptz`; the application timezone comes from a settings row or env, never the container clock.
- Case-insensitive uniqueness (emails) uses CITEXT or a functional index, not app-side lowercasing.

### Query efficiency
- New query shapes have a supporting index; `EXPLAIN` on a realistic data size shows no sequential scan on a large table.
- "Only one may exist" races (singleton registration) use a transaction-scoped advisory lock.
- Rotation chains and counters use `SELECT ... FOR UPDATE`, not optimistic retries.
- Unbounded JSONB columns have a size expectation written down.

### Secrets & config
- Connection strings printed by a provider are reshaped for the driver: scheme, `ssl=` not `sslmode=`, explicit `ssl=disable` on internal endpoints without TLS.
- `pool_pre_ping` is on when the provider drops idle connections.

### Testing
- Sequences advance on rolled-back inserts; tests that assert ids reset them per test.
- A separate test database is created by an init script; `TEST_DATABASE_URL` is never the dev URL.

### Operations
- The backup/restore drill in RUNBOOK.md has been run at least once against a scratch database.
