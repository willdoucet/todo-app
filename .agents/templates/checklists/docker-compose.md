## Docker Compose

### Operations
- Every service has a healthcheck; dependents use `depends_on` with `condition: service_healthy`.
- The dev build target mounts source for reload; the prod target runs as a non-root user with no test dependencies.
- Anything that writes to its working directory (schedulers, caches) has a writable path under the non-root user.
- Optional stacks (visual tests, load tests) sit behind `profiles` so the default `up` stays fast.
- `node_modules` uses an anonymous volume so host and container installs do not collide.
- The test database is created by an init script on first run; `TEST_DATABASE_URL` is distinct from the dev URL.

### Secrets & config
- `.env` is git-ignored; `.env.example` lists every variable with a generation command and never a value.
- Inspecting a container's environment uses names-only or existence-check filters on the container side; `exec <svc> env` is never run bare.

### Testing
- The exact `exec` / `run --rm` commands live in development-commands.md and are the ones CI runs.
- After a model or schema change the API container is restarted when hot reload does not reflect the runtime state.
