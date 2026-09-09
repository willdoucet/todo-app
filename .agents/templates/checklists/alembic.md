## Alembic

### Data & migrations
- Autogenerate output is reviewed by hand: it misses enum value changes, partial indexes, CHECK constraints, server defaults, and CITEXT.
- Type conversions PostgreSQL cannot cast implicitly carry an explicit `postgresql_using=`.
- Every revision has a real `downgrade()`; a destructive drop's downgrade recreates the table (empty is acceptable after an archive window, and the docstring says so).
- Multi-instance deploys use expand/contract: add nullable → backfill → add constraint; never rename a column in place.
- Archive-then-drop: a legacy table kept read-only for a soak window gets a dated TODOS.md item to drop it.
- Data migrations are idempotent, batched, and never import ORM models (schema drift breaks old revisions).
- `alembic heads` shows exactly one head before shipping; branches are merged.

### Operations
- Migrations run on container start or as an explicit release step, never both; development-commands.md says which.
- Inside a container exec session the virtualenv path may be needed explicitly (`.venv/bin/alembic`).
- The migration that ships with a release is listed in RUNBOOK.md with its reversibility.

### Testing
- CI applies `upgrade head` to an empty database and `downgrade base` back on every PR that adds a revision.
- A test asserts the models and the migrated schema agree (autogenerate produces an empty diff).
