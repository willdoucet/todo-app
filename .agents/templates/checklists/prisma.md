## Prisma

### Data & migrations
- `migrate dev` output is committed; releases run `migrate deploy`; `db push` never touches production.
- Every relation declares `onDelete`; enum changes go through a migration.
- Soft delete is filtered in one shared client extension, not per query.

### Query efficiency
- `select` / `include` are explicit; no per-row query inside a loop.
- Multi-write units use `$transaction`; interactive transactions stay short.

### Secrets & config
- `DATABASE_URL` comes from env; the connection limit is set for the runtime (serverless vs. long-lived).

### Testing
- The test database is separate and migrated in CI with `migrate deploy` before tests run.
