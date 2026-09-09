## pytest

### Testing
- Unit and integration suites are separate directories; integration tests require the test database and say so with a marker.
- Fixture scopes are deliberate: session-scoped engines pair with session loop scope for async fixtures and tests.
- Global state installed at more than one scope: the broadest install is a function-scoped autouse fixture so it re-installs after any narrower per-test reset.
- Tests that assert ids reset sequences after `create_all`; rolled-back inserts still advance sequences.
- Code that tests exercise with a hand-built `argparse.Namespace` reads flags via `getattr(args, "flag", default)`.
- Tests assert response bodies and side effects (rows written, jobs enqueued, files stored), not only status codes.
- Cross-cutting guarantees (auth on every route, docs disabled) have a structural test alongside the behavioral one.
- Tests run through the command policy in development-commands.md; the CI command is identical to the local one.
- Byte-identical failure responses have a test that compares bodies across every failure reason.
