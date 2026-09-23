# Backup-restore drill

This drill proves that production's backups restore. A backup that has never been restored
is unproven. The procedure restores a real restore point into a **scratch** cluster, counts
what came back, records the observed numbers, and destroys the scratch cluster. It never
touches `mealy-app-prod-db`.

This deployment has one operator by design, so the usual mitigation of "train two people"
does not apply here. What has to survive is the numbers written in the log below: how old
the restore point was, how long the restore took, and how many rows came back. The
operator's memory is not enough.

| | |
|---|---|
| Owner | willdoucet |
| Last executed | never. The first execution is M8's "Between the PRs" step 5, after PR1a |
| Estimated duration | 60–90 min for both paths. Most of it is waiting for `fly pg create` |
| Risk | Low for production (read-only against it). Scratch clusters cost money until destroyed |
| Cadence | Every 3 months as a starting point. The operator sets the real interval at the first execution (open question 2) and records it in the log. The re-run triggers below matter more than the interval |
| Minimum flyctl | v0.4.102 |
| Builds on | the `pg_dump` → restore-probe → count-verify sequence in `.agents/plans/features/mealboard-main-page-updates/ROLLOUT.md` |

## What is being restored

Production runs **unmanaged Fly Postgres Flex**: app `mealy-app-prod-db`, image
`flyio/postgres-flex:17.2`, volume `pg_data`, scheduled snapshots with 5-day retention. It is
not Managed Postgres. It has two separate restore mechanisms, and the drill proves each
one:

| Mechanism | What it is | Listed by | Restored by |
|---|---|---|---|
| Volume snapshots | a daily snapshot of the `pg_data` volume | `fly volumes snapshots list <vol> -a mealy-app-prod-db` | `fly pg create --snapshot-id <id>` |
| Continuous backups | WAL archiving to a Tigris bucket, allowing point-in-time recovery | `fly pg backup list -a mealy-app-prod-db` | `fly pg backup restore <new-app> --restore-target-time <RFC3339>` |

Having one configured says nothing about the other. On 2026-09-12 snapshots were configured
but none existed, and continuous backups were off.

### The failure mode this drill exists for: a volume move resets snapshot history

Fly can move the database machine to a new host. It creates a **new volume in a new zone**,
marks the old one `pending_destroy`, keeps the data, and **drops every snapshot**, because the
new volume's snapshot timeline starts at zero. Nothing warns you, and the app stays healthy.
`fly volumes list` does not even show the old volume without `--all`. That is how production
ran with no restore point on 2026-09-12. The recovery-point objective that matters is the
age of the oldest existing restore point, not the configured retention. Smoke check 9 now
watches this at every release and daily.

## Rules that are never skipped

- **Never restore into `mealy-app-prod-db`.** Every restore command below takes the *new*
  scratch app's name as its target.
- **Scratch names carry the date**, `mealy-app-drill-YYYYMMDD` and
  `mealy-app-drill-pitr-YYYYMMDD`, so a leftover from a crashed drill cannot collide with a
  new one.
- **The first step is always to destroy leftovers**, even if "we cleaned up last time".
- **Always pass `-a mealy-app-prod-db`** to snapshot commands. From `backend/`, flyctl infers
  `mealy-app-prod` from `fly.toml` and fails with "volume does not belong to app".
- `fly pg create` prints the scratch cluster's credentials. Do not paste them anywhere; they
  die with the app. Never print production's `DATABASE_URL`.

## 0. Before the drill: is there anything to restore? (item 12)

- [ ] **Continuous backups are enabled.** If the list says they are not enabled, enable them:
      ```bash
      fly pg backup list -a mealy-app-prod-db
      ```
      ```bash
      fly pg backup enable -a mealy-app-prod-db
      ```
      Record in the log whether enabling reported a cost (it creates a Tigris bucket), and
      whether it restarted the database machine (`fly status -a mealy-app-prod-db`).
- [ ] **A scheduled snapshot has landed on the current volume.** The volume id comes from the
      listing each time, because a host migration changes it:
      ```bash
      fly volumes list --json -a mealy-app-prod-db
      fly volumes snapshots list <vol> -a mealy-app-prod-db --json
      ```
      The first time you see a snapshot on a new volume, write its time into the
      **restore-point log** below. That time is the real recovery-point objective. The
      configured retention is not.
- [ ] `fly status -a mealy-app-prod-db` notes whether an image update is available (17.2 →
      17.7 was available on 2026-09-12). Applying it is a re-run trigger for this drill.

## 1. Clear leftovers

```bash
fly apps list | grep mealy-app-drill
```

Destroy every app that command lists. Read each name before confirming. It must start with
`mealy-app-drill`:

```bash
fly apps destroy <leftover-drill-app> --yes
```

## 2. Path 1: restore a volume snapshot

1. Pick the newest snapshot and note its id, its `created_at`, and its age now:
   ```bash
   fly volumes list --json -a mealy-app-prod-db
   fly volumes snapshots list <vol> -a mealy-app-prod-db --json
   date -u +%FT%TZ
   ```
2. Restore it into a new scratch cluster. Use production's image, so the Postgres version
   matches, and a volume at least as large as production's (`size_gb` from the listing):
   ```bash
   DRILL="mealy-app-drill-$(date -u +%Y%m%d)"; echo "$DRILL"
   date -u +%T
   fly pg create --name "$DRILL" --snapshot-id <vs_id> --image-ref flyio/postgres-flex:17.2 \
     --region sjc --initial-cluster-size 1 --vm-size shared-cpu-1x --volume-size <size_gb>
   date -u +%T
   ```
   The two `date` lines give the **restore duration**.
3. Count what came back (§4), connected to `"$DRILL"`.
4. Destroy it, and confirm it is gone:
   ```bash
   fly apps destroy "$DRILL" --yes
   fly apps list | grep mealy-app-drill
   ```
   The second command must print nothing.

## 3. Path 2: point-in-time restore from continuous backups

1. List recovery points and choose a target time inside the recoverable window. Recent is
   best, for example 15 minutes ago, and it must be RFC 3339 UTC:
   ```bash
   fly pg backup list -a mealy-app-prod-db
   date -u -v-15M +%FT%TZ
   ```
   On Linux the second command is `date -u -d '15 minutes ago' +%FT%TZ`. If the restore
   fails with `recovery ended before configured recovery target was reached`, no archived
   commit falls after the target (a quiet database): choose an earlier time, inside the
   window the listing shows.
2. Restore into a second scratch cluster. `-a` is the **source**; the positional argument is
   the new app:
   ```bash
   PITR="mealy-app-drill-pitr-$(date -u +%Y%m%d)"; echo "$PITR"
   date -u +%T
   fly pg backup restore "$PITR" -a mealy-app-prod-db --restore-target-time <RFC3339> \
     --image-ref flyio/postgres-flex:17.2
   date -u +%T
   ```
   Then, before anything else, list the scratch cluster's secret **names** (never values):
   ```bash
   fly secrets list -a "$PITR"
   ```
   If it carries a WAL-archive setting (a name such as `S3_ARCHIVE_CONFIG`), it may be
   archiving into production's backup bucket. Destroy it now (step 4), record the names in
   the log, and settle how the restore isolates its archive before the next drill. Not yet
   observed: the first drill answers it.
3. Count what came back (§4), connected to `"$PITR"`.
4. Destroy it, and confirm it is gone:
   ```bash
   fly apps destroy "$PITR" --yes
   fly apps list | grep mealy-app-drill
   ```

## 4. Count what came back

Connect to the scratch cluster, never production. Find the app database with `\l` (the one
that is not `postgres`, `repmgr` or `template*`), then switch to it with `\c`:

```bash
fly pg connect -a <scratch-app>
```

First, on each scratch cluster, before any count:

```sql
SELECT pg_is_in_recovery();
SHOW archive_mode;
SHOW archive_command;
```

- `pg_is_in_recovery()` must be `f`. `t` means WAL is still replaying and the counts would
  be partial: wait and re-run. On the point-in-time path the restore duration ends when it
  first reads `f`, not when `fly pg backup restore` returns.
- If archiving is on and the command names a bucket, the scratch cluster may be writing into
  production's backups: destroy it now, record it in the log, and settle how the restore
  isolates its archive before the next drill (the same rule as §3 step 2).

```sql
SELECT version_num FROM alembic_version;
SELECT 'users' AS tbl, count(*) FROM users
UNION ALL SELECT 'tasks', count(*) FROM tasks
UNION ALL SELECT 'items', count(*) FROM items
UNION ALL SELECT 'meal_entries', count(*) FROM meal_entries
UNION ALL SELECT 'family_members', count(*) FROM family_members
UNION ALL SELECT 'responsibilities', count(*) FROM responsibilities
UNION ALL SELECT 'assets', count(*) FROM assets;
SELECT to_regclass('public.job_heartbeats') IS NOT NULL AS job_heartbeats_exists;
```

- `assets` is the R2 object manifest. A stale copy of it is what can cost real files in a
  real restore
  ([incident-diagnostics.md → A real restore into production](./incident-diagnostics.md#a-real-restore-into-production)).
- `job_heartbeats`: if the table exists (PR1b onwards), also run
  `SELECT count(*) FROM job_heartbeats;`. Its rows are copies, and on a scratch cluster
  they read as stale, which is expected. If it does not exist (the PR1a drill), record
  `n/a — table not in this schema` rather than a failed count.
- For comparison, run the same `SELECT`s against production
  (`fly pg connect -a mealy-app-prod-db`) inside a read-only transaction, because that
  session is a superuser: start with `BEGIN READ ONLY;` and end with `ROLLBACK;`. The
  restored counts should be at or just below production's. The gap is the writes since
  the restore point.

## 5. Record, then re-run when a trigger fires

Fill in one row per path in the execution log. Re-run the whole drill:

- after a Postgres major-version upgrade, or an image update of `mealy-app-prod-db`;
- after any change to the backup tooling or its settings (`fly pg backup enable` / `config`);
- when **the volume id changed** (a host migration), because the snapshot history reset;
- on the cadence in the header.

---

## Execution log

| Date (UTC) | Operator | Path | Restore point (id / target time) | Point's age | Restore duration | Row counts (users · tasks · items · meal_entries · family_members · responsibilities · assets · job_heartbeats) | Scratch destroyed | Notes |
|---|---|---|---|---|---|---|---|---|

## Restore-point log

When the restore posture changed, and what was observed. A new volume id, backups enabled,
or the first snapshot seen on a volume each get a row.

| Date (UTC) | Event | Volume | Observation |
|---|---|---|---|
| 2026-09-12 | Host migration found: machine `6835444b795398` created 2026-09-11T23:31:01Z in zone `d2a4`; the previous volume `pending_destroy` in zone `76a8` | `vol_4qlnz9q037wl2qwr` | "No snapshots available"; `fly pg backup` disabled. **No restore point existed.** |
