## Express

### API & trust boundaries
- Every route validates body, params, and query with a schema before use.
- Auth middleware is applied per router; a test enumerates the route table and asserts the middleware on every non-public route.
- The error handler is registered last; production responses never include stack traces.
- `helmet`, a CORS allowlist from env, body-size limits, and rate limiting on auth routes are present.

### Rendering & state
- Async handlers are wrapped so rejections reach the error handler; no request can hang on an unhandled promise.
- Outbound calls have timeouts.

### Operations
- Graceful shutdown closes the server and the database pool; a health endpoint reports the version.
- Logs are structured with a request id and never contain credentials.

### Testing
- Tests use supertest against the app object, not a live port; database state is isolated per test.
