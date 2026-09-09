# Config refinements

Loaded by `init-project` steps N3 and A3. `.agents/config.json` is edited with python3 only
(load, mutate, dump with `indent=2, sort_keys=True, ensure_ascii=False`, trailing newline);
the helpers read it on every call, so a hand edit that breaks the JSON breaks every skill.
`framework init` wrote the file; this skill refines it. The example lives at
`.agents/config.example.json` when you need to see a full shape.

## Fields to set

| Field | Set to | Notes |
|---|---|---|
| `project_name` | slug of the product name | Used as `PROJECT` in every banner |
| `project_shape` | `web-split` | The only supported shape today |
| `default_branch` | the base branch | Confirm with `git symbolic-ref refs/remotes/origin/HEAD` when a remote exists; else ask |
| `vault_path` | leave as `framework init` set it | Confirm the directory exists; create it if the user wants a vault and it is absent |
| `layout.backend_dir` | the backend directory name | Repo-relative, no trailing slash |
| `layout.frontend_dir` | the frontend directory name | Same |
| `doc_map.rules` | rewritten for the layout | See below |
| `doc_map.exempt` | keep the defaults; add generated or vendored directories | Tests, lockfiles, images stay exempt |
| `design_watched_files` | the guidelines doc plus the token file | The file that defines design tokens (chosen in the styling layer) |
| `modules` | per the module questions | `learning`, `design_sync`, `learning_summaries` |

Leave `schema_version`, `framework_version`, `paths`, and `doc_guard_mode` alone unless the
user asks; `doc_guard_mode` is `strict`, `pr-strict`, or `ci-only`.

## Doc-map rules

Every code area gets exactly one owning doc section. Rules are glob lists; the first match
wins. Write them against the real layout and the chosen framework's conventions, one rule per
row of this table, and drop rows the stack does not have:

| Code area | Typical globs (relative to the layout dirs) | Doc | Section |
|---|---|---|---|
| Models and migrations | `<backend_dir>/**/models*`, `<backend_dir>/**/migrations/**` | `BACKEND_STRUCTURE.md` | Database Schema |
| Routes, controllers, the app entrypoint | `<backend_dir>/**/routes/**`, `<backend_dir>/**/api/**`, `<backend_dir>/**/main.*` | `BACKEND_STRUCTURE.md` | API Endpoints |
| Request and response schemas | `<backend_dir>/**/schemas*` | `BACKEND_STRUCTURE.md` | Data Validation |
| Services, jobs, storage, auth | `<backend_dir>/**/services/**`, `<backend_dir>/**/jobs/**`, `<backend_dir>/**/storage/**`, `<backend_dir>/**/auth/**` | `BACKEND_STRUCTURE.md` | Code Organization |
| Pages and the router | `<frontend_dir>/src/pages/**`, `<frontend_dir>/src/routes/**`, `<frontend_dir>/src/App.*` | `APP_FLOW.md` | Screen Inventory |
| Components, features, hooks, lib | `<frontend_dir>/src/components/**`, `<frontend_dir>/src/features/**`, `<frontend_dir>/src/hooks/**`, `<frontend_dir>/src/lib/**` | `FRONTEND_STRUCTURE.md` | Directory Overview |
| Design tokens and global styles | the token file, `<frontend_dir>/src/styles/**` | `FRONTEND_GUIDELINES.md` | Color Palette |
| Dependency manifests | `<backend_dir>/<manifest>`, `<frontend_dir>/package.json` | `TECH_STACK.md` | Dependencies |
| Container and env files | the compose file, both container build files, `.env.example` files | `development-commands.md` | Full Stack |
| CI workflows | `.github/workflows/**` or the git host's equivalent | `TECH_STACK.md` | CI/CD Pipeline |

Section names must match a heading that exists in the generated doc; `/update-docs` and the
staleness gate look them up by name. When the stack has an area this table lacks (a mobile
directory, an infrastructure directory, a shared package), add a rule or an exempt entry in
the same change, and add the matching section to the owning doc.

## Verify

```bash
eval "$("$BIN/ctx")"                                        # loads, or prints the JSON error
"$BIN/doc-guard" --explain "<backend_dir>/path/to/a/model"  # one probe per rule
"$BIN/doc-guard" --explain "<frontend_dir>/src/pages/Home"  # unmapped paths print no owner
```

In adopt mode probe with real files from the survey. In new mode probe with the paths the
`FRONTEND_STRUCTURE.md` and `BACKEND_STRUCTURE.md` blueprints promise; the rules and the
blueprints must agree before Phase 1 creates the files.
