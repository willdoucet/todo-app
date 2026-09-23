# Fixtures for the operator scripts

- `healthz_healthy.json` is the healthy example of the `/healthz.jobs` contract pinned in the
  M8 plan (item 15). The Settings MSW fixtures copy the same example. There is no cross-suite
  contract test, because the api container does not mount `infra/`. The first PR1b smoke run
  is the integration point, and a mismatch there fails loudly (exit 1).
- `fly_*.json` and `fly_pg_backup_list.txt` follow flyctl v0.4.102's documented output shapes.
  They were not captured from production (M8 PR1a assumption 5). `fly pg backup list` has no
  `--json`, so the script reads timestamps out of its table, not columns. The first real
  smoke run is the integration point. A shape the parsers do not recognise ends in exit 2
  (tooling), never a pass. When that happens, replace the fixture with the real output and
  redact it first.
- `cloudflare_*.json` follow the Cloudflare v4 API response envelope
  (`{"success": true, "result": ...}`). `cloudflare_transform_rules.json` carries a dummy
  `X-Origin-Verify` value on purpose: the drift tests assert it never reaches stdout,
  stderr, or the diff.
