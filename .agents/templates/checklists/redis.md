## Redis

### Data & migrations
- Keys are namespaced (`app:feature:id`) and every key has a TTL or a comment saying why it must not.
- Check-and-set patterns use `SET NX`, a Lua script, or `WATCH`/`MULTI`, never read-then-write.
- Values are versioned or self-describing so a deploy can change the shape without a flush.

### Secrets & config
- The URL comes from env; hosted instances use `rediss://` with certificate verification.
- Local and production URLs differ only in scheme and host; the app tolerates both.

### Operations
- The eviction policy is known and the app survives a miss on every cached key.
- The connection pool is sized to the worker count and closed on shutdown.
- A Redis outage degrades (no cache, queued jobs wait) rather than 500s the request path.

### Testing
- Tests use a fake client or a dedicated database index and never `FLUSHALL` a shared instance.
