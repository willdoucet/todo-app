## SQLAlchemy

### Data & migrations
- Enum columns return enum members, not strings; comparisons use the enum, never a raw string.
- A new NOT NULL or boolean column on an existing table is backfilled in the migration, or the read schema tolerates NULL until it is.
- Soft delete: every read goes through one shared statement builder that filters `deleted_at IS NULL`; uniqueness is a partial index `WHERE deleted_at IS NULL`.
- Every FK relationship declares its delete behavior deliberately (CASCADE / SET NULL / RESTRICT) and the docs say which.
- Self-referential FKs that form chains use `use_alter=True` and SET NULL so rows can be deleted.

### Query efficiency
- Relationships the response touches are `selectinload`ed in the query builder; no per-row lazy loads in a list endpoint.
- `with_for_update()` locks are held for the whole unit of work; no per-iteration flush or commit releases the lock mid-loop.
- New query shapes have a supporting index; the migration adds it.
- Engine `echo` is env-gated and defaults to off; `echo=True` is never committed.

### Background jobs
- Async engine used from a sync entry point (job worker, CLI) gets a fresh event loop per call and disposes the engine before the loop closes; pooled connections must not span loops.
- `pool_pre_ping=True` where the provider drops idle connections.

### Secrets & config
- Async drivers use the `+asyncpg` (or equivalent) scheme; `sslmode=` is not a valid asyncpg kwarg (use `ssl=`); internal-network endpoints without TLS need `ssl=disable` explicitly.

### Testing
- Integration tests target `TEST_DATABASE_URL`, never the dev database.
- SAVEPOINT-based isolation does not reset sequences; tests that assert ids reset sequences after `create_all`.
- Session-scoped engines set the pytest-asyncio fixture and test loop scopes to `session`.
