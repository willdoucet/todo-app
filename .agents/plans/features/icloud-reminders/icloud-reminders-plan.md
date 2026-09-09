# iCloud Reminders Integration for Lists

## Context

The app needs two-way sync with Apple Reminders via CalDAV VTODO protocol, reusing the existing iCloud Calendar integration infrastructure (credentials, Celery workers, sync patterns). This also requires evolving the Task model to align with Apple Reminders fields: replacing `important` (bool) with `priority` (int), adding subtasks (unlimited nesting), and adding sections (first-class feature within lists).

**Split into two phases:**
- **Phase 1**: Task model changes (priority, subtasks, sections) + frontend UI updates
- **Phase 2**: iCloud Reminders sync engine, settings UI, badges

## Review Decisions

### CEO Review (HOLD SCOPE mode)
1. **Composite sync status** — Add `reminders_status`, `reminders_last_error`, `reminders_last_sync_at` columns to CalendarIntegration. Overall `status` = worst-of-both. Settings UI shows separate badges per feature.
2. **Defer CalendarIntegration → CloudIntegration rename** to a follow-up PR after Phase 2 ships.
3. **Server-side cycle detection** for subtask parent_id — walk ancestor chain before save, reject with 400 on cycle.
4. **Extract `sync_base.py`** with shared helpers (credential loading, iCloud connection, status tracking) used by both sync engines.
5. **2-level eager load** for subtasks — load children + grandchildren, lazy-load deeper on UI expand.
6. **Single migration** for Phase 1 — accept brief table lock on `DROP COLUMN important`.
7. **Validate parent in same list** — parent_id must reference a task in the same list_id.
8. **Validate section in same list** — section_id must belong to the task's list_id.
9. **Add `section_id` index** on tasks table for grouping queries.

### Eng Review
10. **CRUD-level push triggers** — Put iCloud push-trigger logic (Celery dispatch on synced task edit/delete) in `crud_tasks.py`, not `routes/tasks.py`. Also refactor existing `routes/calendar_events.py` push triggers into `crud_calendar_events.py` for consistency.
11. **Load-modify-save pattern** for `update_task` — Switch from bulk UPDATE to load→validate→modify→commit to support cycle detection, cross-list validation, and completed_at auto-set.
12. **Drop `is_synced` DB column** — Derive `is_synced` in Pydantic response schema from `calendar_integration_id IS NOT NULL`. Eliminates data consistency risk.
13. **Fix default task limit** — Change `crud_tasks.get_tasks` default limit from 10→100 to match route-level default.
14. **5 additional test cases** — No-DUE VTODO, duplicate UID race, push exhaustion, synced-list-delete-blocked, disconnect cleanup.

---

## Phase 1: Task Model Enhancement + UI

### Step 1.1: Alembic Migration

Create migration: `add_priority_subtasks_sections_sync_metadata`

**`tasks` table changes:**
- Drop `important` (Boolean)
- Add `priority` (Integer, default=0, NOT NULL) — 0=none, 1=high, 5=medium, 9=low
- Add `parent_id` (Integer, FK→tasks.id, SET NULL, nullable) — self-referential for subtasks
- Add `section_id` (Integer, FK→sections.id, SET NULL, nullable) — with index
- Add `sort_order` (Integer, default=0, NOT NULL)
- Add `completed_at` (DateTime, nullable) — tracks when completed (for Reminders sync)
- Add sync metadata: `external_id`, `etag`, `last_modified_remote`, `sync_status`, `calendar_integration_id` (FK→calendar_integrations.id, SET NULL)
- Add unique constraint: `(external_id, calendar_integration_id)`

**New `sections` table:**
- `id` (PK), `name` (String, NOT NULL), `list_id` (FK→lists.id, CASCADE), `sort_order` (Integer, default=0), `external_id` (String, nullable), `created_at`, `updated_at`

**`lists` table changes:**
- Add `external_id` (String, nullable) — CalDAV calendar URL for synced lists
- Add `calendar_integration_id` (FK→calendar_integrations.id, SET NULL, nullable)
- ~~`is_synced` (Boolean)~~ — **REMOVED per eng review #12**: derived in Pydantic schema instead

**Data migration:** Convert `important=True` → `priority=1`, `important=False` → `priority=0`

### Step 1.2: Update SQLAlchemy Models

**File:** `backend/app/models.py`

Task model:
- Replace `important` with `priority`, add `parent_id`, `section_id`, `sort_order`, `completed_at`, sync metadata columns
- Add relationships: `children` (back_populates="parent"), `parent` (remote_side=[id]), `section`

New Section model:
- Fields as described above
- Relationships: `list` (back_populates="sections"), `tasks` (back_populates="section")

List model:
- Add `external_id`, `calendar_integration_id`
- Add relationships: `sections` (cascade="all, delete-orphan"), `integration`

Calendar model:
- Add `is_todo` (Boolean, default=False) — distinguishes reminder lists from event calendars

CalendarIntegration model (composite status for Phase 2):
- Add `reminders_status` (Enum, nullable) — ACTIVE/SYNCING/ERROR, null when no reminders connected
- Add `reminders_last_error` (String, nullable)
- Add `reminders_last_sync_at` (DateTime, nullable)
- Overall `status` field remains as worst-of-both (ERROR if either fails)

### Step 1.3: Update Pydantic Schemas

**File:** `backend/app/schemas.py`

- TaskBase: `important` → `priority: int = Field(default=0, ge=0, le=9)`, add `parent_id`, `section_id`
- TaskUpdate: same field swap, add `completed_at`
- Task (response): add `priority`, `parent_id`, `section_id`, `is_synced` (computed from `calendar_integration_id is not None`), `children`, `completed_at`
- New: SectionBase, SectionCreate, SectionUpdate, Section (response)
- List (response): add `is_synced` (computed from `calendar_integration_id is not None`), `sections`

### Step 1.4: CRUD Updates

**File:** `backend/app/crud_tasks.py`
- **Refactor `update_task` to load-modify-save** (per eng review #11): load Task object, apply validations, modify fields, commit
- Handle `priority`, `parent_id`, `section_id` in create/update
- When `completed` → True: set `completed_at = utcnow()`; when False: clear `completed_at`
- Eager-load `children` 2 levels deep (selectinload children → selectinload children). Deeper levels lazy-loaded on UI expand.
- **Cycle detection:** Before setting `parent_id`, walk ancestor chain (max 50 iterations). If cycle found or depth exceeded, return 400.
- **Cross-list validation:** `parent_id` must reference a task with the same `list_id`. `section_id` must reference a section with the same `list_id`. Return 400 if violated.
- **Fix default limit** from 10→100 (per eng review #13)

**New file:** `backend/app/crud_sections.py`
- `get_sections(db, list_id)` — ordered by sort_order
- `create_section`, `update_section`, `delete_section`
- `reorder_sections(db, list_id, ordered_ids)`

### Step 1.5: Section API Routes

**New file:** `backend/app/routes/sections.py`
- `GET /lists/{list_id}/sections`
- `POST /lists/{list_id}/sections`
- `PATCH /sections/{section_id}`
- `DELETE /sections/{section_id}`
- `POST /lists/{list_id}/sections/reorder`

Register in `backend/app/main.py`.

### Step 1.6: Frontend — Priority Replaces Important

**File:** `frontend/src/components/lists/TodoForm.jsx`
- Replace "Mark as Important" toggle with **segmented control** (pill buttons): `None | Low | Med | High`
- Active pill uses priority color fill. Inactive pills use `bg-warm-sand text-text-secondary`
- Matches existing category filter pill pattern from Responsibilities page

**File:** `frontend/src/components/lists/TaskItem.jsx`
- Replace star icon with priority flag indicator (inline SVG, `w-[13px] h-[13px]` matching current star size):
  - High (1): `text-red-600 dark:text-red-400` (matches overdue color semantic)
  - Medium (5): `text-amber-500 dark:text-amber-400` (matches current important star)
  - Low (9): `text-text-secondary dark:text-gray-400` (subtle, warm)
  - None (0): hidden (no indicator)
- Flag icon replaces star icon in same position (after title, before metadata zone)
- Dark mode: use established dark mode color mappings

**File:** `frontend/src/components/lists/TaskItem.test.jsx`
- Update `createTask()` helper: `important` → `priority: 0`
- Update assertions for priority indicators (red/amber/gray/hidden)

**File:** `frontend/src/components/lists/TodoForm.test.jsx`
- Update for segmented priority selector

### Step 1.7: Frontend — Sections UI

**File:** `frontend/src/components/lists/TaskListView.jsx`
- Group tasks by `section_id` (null = unsectioned group, rendered first)
- Render section headers (collapsible)
- "Add Section" button at bottom of list (secondary button style)

**New file:** `frontend/src/components/lists/SectionHeader.jsx`
- Visual style: `text-xs font-semibold uppercase tracking-wider text-text-secondary` (matches Responsibilities category headers)
- Background: `bg-warm-beige dark:bg-gray-800` sticky top within scroll container
- Chevron toggle (w-3.5 h-3.5) for collapse/expand, rotates 90° on collapse
- Task count badge: `text-xs text-text-muted` after section name
- Edit/delete buttons: hover-reveal (same pattern as TaskItem action buttons)
- **Empty section state:** Subtle dashed outline (`border-dashed border-card-border`), warm-beige tint, "Add a task" text-muted with + icon. Actionable — clicking adds a task to this section.
- Keyboard: Enter/Space toggles collapse, Tab navigates between sections
- **Collapse animation:** Section content uses `transition-all duration-150 ease-out` with `max-height` or `grid-template-rows: 0fr → 1fr` pattern. Chevron rotates 90° with `transition-transform duration-150`.

**File:** `frontend/src/pages/ListsPage.jsx`
- Fetch sections when list selected
- API calls for section CRUD

### Step 1.8: Frontend — Subtasks UI

**File:** `frontend/src/components/lists/TaskItem.jsx`
- Collapse/expand chevron (w-3 h-3) before checkbox when task has children
- Children rendered indented below parent: `pl-6` (24px) per nesting level
- **Mobile (<640px):** Cap visual indentation at 2 levels max (32px). Deeper tasks render flat with a `text-xs text-text-muted` parent breadcrumb label
- Desktop: full indentation up to eager-load depth (2 levels, deeper on expand)
- Keyboard: Enter/Space toggles expand, Tab navigates into children

**File:** `frontend/src/components/lists/TaskListView.jsx`
- Filter tasks with `parent_id` from top-level; render nested under parents

**File:** `frontend/src/components/lists/TodoForm.jsx`
- "Add Subtask" action pre-fills `parent_id`

### Phase 1 Testing

**Backend integration tests:**
- Update existing task tests: `important` → `priority` field swap
- Subtask creation/retrieval with 2-level nesting
- **Cycle detection:** A→B→C→A rejected with 400
- **Cross-list parent rejected:** parent in List 1, child in List 2 → 400
- **Section-list mismatch rejected:** section from List 1 assigned to task in List 2 → 400
- New `test_sections_api.py`: full CRUD + reorder + cascade delete behavior
- Migration test: verify `important=True` → `priority=1` conversion

**Frontend tests:**
- TaskItem: priority indicators (high/medium/low/none), subtask expand/collapse
- TodoForm: priority selector, parent_id dropdown
- SectionHeader: edit/delete, task count badge

---

## Phase 2: iCloud Reminders Sync Engine

### Step 2.1: CalDAV VTODO Client Functions

**File:** `backend/app/services/caldav_client.py` — add alongside existing VEVENT functions:

- `list_reminder_lists(principal)` — filter calendars by VTODO support (supported-component-set)
- `fetch_todos(calendar)` — fetch incomplete + recently completed VTODOs (no date windowing)
- `vtodo_to_task_data(vtodo)` — map SUMMARY→title, DESCRIPTION→description, DUE→due_date, PRIORITY→priority, STATUS→completed, COMPLETED→completed_at, RELATED-TO→parent_external_id, UID→external_id
- `task_data_to_vtodo(task_data)` — reverse mapping for push
- `create_remote_todo(calendar, task_data)` — create VTODO, return UID
- `update_remote_todo(calendar, uid, task_data)` — update existing VTODO
- `delete_remote_todo(calendar, uid)` — delete VTODO

### Step 2.2: Extract Shared Sync Base + Reminders Sync Engine

**New file:** `backend/app/services/sync_base.py`
- `load_integration_with_credentials(db, integration_id)` — loads integration, decrypts password, connects to iCloud
- `update_sync_status(db, integration_id, status, error=None)` — shared status update logic
- `resolve_calendar_rows(db, integration, is_todo=False)` — gets Calendar rows (with legacy fallback)
- Refactor existing `sync_engine.py` to import from `sync_base.py`

**New file:** `backend/app/services/reminders_sync_engine.py`

Uses `sync_base.py` helpers, implements VTODO-specific logic:
- `pull_reminders_from_icloud(db, integration_id)` — for each selected reminder list (Calendar rows with `is_todo=True`): fetch VTODOs, create/update/delete local Tasks. Auto-create List if first sync. Auto-assign to `integration.family_member_id`. Two-pass for subtask resolution (create all tasks first, then resolve parent_external_id → parent_id).
- `push_task_to_icloud(db, task_id)` — push PENDING_PUSH task changes as VTODO
- `push_task_delete_to_icloud(db, external_id, integration_id)` — delete VTODO from iCloud
- Conflict resolution: same last-write-wins as calendar sync

Key differences from calendar sync:
- No date-range windowing — fetch all incomplete + completed in last 30 days
- Lists auto-created (always new, never merge with existing)
- Subtask parent resolution via RELATED-TO → parent_external_id → parent_id FK

### Step 2.3: Add `is_todo` to Calendar Model

**Migration:** `add_is_todo_to_calendars`
- Add `is_todo` (Boolean, default=False) to `calendars` table

### Step 2.4: Integration Routes for Reminders

**File:** `backend/app/routes/integrations.py` — add new endpoints:

- `POST /integrations/icloud/validate-reminders` — reuse existing credentials (by integration_id), list available reminder lists
- `POST /integrations/icloud/connect-reminders` — add Calendar rows (is_todo=True) to existing integration, dispatch initial sync
- `POST /integrations/{id}/sync-reminders` — manual sync for reminders only
- `DELETE /integrations/{id}/reminders` — disconnect reminders only: remove reminder Calendar rows (is_todo=True), clear sync metadata on associated tasks (set external_id=null, sync_status=null, calendar_integration_id=null). Tasks and lists remain as local data. Cancel any pending push tasks.

**New schemas:**
- `ICloudReminderListInfo`: url, name, color, task_count, already_synced_by
- `RemindersConnectPayload`: integration_id, selected_lists
- Extend `CalendarIntegrationResponse`: add `reminder_lists` (Calendar rows where is_todo=True)

### Step 2.5: Celery Tasks for Reminders

**File:** `backend/app/tasks.py`

- `sync_all_reminders()` — periodic task, sync all integrations that have reminder lists
- `sync_single_reminders_integration(integration_id)` — initial + manual sync
- `push_task_to_icloud_task(task_id)` — push task changes as VTODO
- `push_task_delete_to_icloud_task(external_id, integration_id)` — push task deletion

**File:** `backend/app/celery_app.py`
- Add `sync-icloud-reminders` to beat schedule (600s), OR call from existing `sync_all_icloud_integrations`

### Step 2.6: CRUD-Level Push Triggers (per eng review #10)

**File:** `backend/app/crud_tasks.py`
- In `update_task`: if task has `external_id`, set `sync_status=PENDING_PUSH` and dispatch `push_task_to_icloud_task.apply_async(args=[task_id], countdown=30)`
- In `delete_task`: if task has `external_id`, dispatch `push_task_delete_to_icloud_task.apply_async(args=[external_id, integration_id], countdown=30)` before deleting

**File:** `backend/app/crud_calendar_events.py` (refactor per eng review #10)
- Move push-trigger logic from `routes/calendar_events.py` into CRUD layer for consistency
- `routes/calendar_events.py` becomes thin route handlers

**File:** `backend/app/crud_lists.py`
- Block deletion of synced lists (`calendar_integration_id IS NOT NULL`) — direct user to Settings to disconnect

### Step 2.7: Frontend — Extend ICloudSettings

**File:** `frontend/src/components/settings/ICloudSettings.jsx`
- Extend IntegrationCard with Reminders sub-section, separated by `border-t border-card-border` divider:
  - **Top half:** Calendar status (existing — calendar names, status badge, sync time)
  - **Bottom half:** Reminders status or "Connect Reminders" button
  - No reminders connected → secondary button "Connect Reminders" (no re-login needed)
  - Connected → show list names with task counts, separate reminders status badge (`reminders_status`), "Sync Now" button, "Disconnect Reminders" link (text-red-600)
  - Separate status badges: "Calendar: Active" (sage-500) and "Reminders: Active" (sage-500) or "Reminders: Error" (red-600)
- Connection flow: click "Connect Reminders" → call validate-reminders (reuses credentials) → show ReminderListSelector → connect

**New file:** `frontend/src/components/settings/ReminderListSelector.jsx`
- Same pattern as CalendarSelector: checkbox list with color dots, task counts per list
- Shows "Already synced by [Member Name]" warning badge for shared lists (disabled by default)
- "Select All / Deselect All" toggle, "Select at least one list" reminder

### Step 2.8: Frontend — iCloud Badges

**File:** `frontend/src/components/lists/ListPanel.jsx`
- Small cloud icon (inline SVG, `w-3.5 h-3.5 text-text-muted`) next to list name for synced lists
- Prevent deletion of synced lists: delete button hidden, tooltip "Disconnect in Settings"
- **Sync progress:** "Syncing reminders..." text-xs text-text-muted banner at top of ListPanel during initial sync (poll until done)

**File:** `frontend/src/components/lists/TaskItem.jsx`
- Small cloud icon (`w-3 h-3 text-text-muted`) in metadata zone (next to due date chip) for tasks with `external_id`
- "Syncing..." text if `sync_status === 'PENDING_PUSH'` (same pattern as calendar events)

**File:** `frontend/src/pages/ListsPage.jsx`
- `is_synced` field from list response drives badge rendering

### Interaction State Table (Phase 1 + 2)

```
  FEATURE                  | LOADING          | EMPTY                        | ERROR              | SUCCESS
  -------------------------|------------------|------------------------------|--------------------|-----------------
  Priority selector        | N/A              | "None" selected by default   | N/A                | Pill highlights
  Section list             | Skeleton headers | Warm empty state + "Add      | Toast: "Failed to  | Section appears
                           |                  | Section" button              | load sections"     | with fade-in
  Empty section            | N/A              | Dashed outline + "Add a      | N/A                | First task fills
                           |                  | task" text-muted + icon      |                    | section
  Subtask tree             | Skeleton indent  | N/A (parent always shown)    | N/A                | Children expand
                           |                  |                              |                    | with fade-in
  Reminders connect flow   | "Validating..."  | No reminder lists found:     | "Failed to connect | "Connected!" badge
                           | spinner on button| "No Reminders lists in this  | — check password"  | + start sync
                           |                  | iCloud account"              |                    |
  Reminders sync progress  | "Syncing         | N/A                          | Error badge +      | Lists appear,
                           | reminders..."    |                              | last_error message | badge clears
                           | banner on Lists  |                              |                    |
  iCloud badge on task     | N/A              | N/A                          | N/A                | Subtle cloud icon
  Synced list delete       | N/A              | N/A                          | "Disconnect in     | N/A
                           |                  |                              | Settings" tooltip  |
```

### Phase 2 Testing

**Backend unit tests:**
- `vtodo_to_task_data`: valid VTODO, missing UID (→None), missing SUMMARY (→None), no DUE date, RELATED-TO parsing
- `task_data_to_vtodo`: round-trip fidelity, priority mapping, completion status
- Priority mapping edge cases: VTODO priority 0/1/5/9 all preserved correctly
- **No-DUE VTODO:** task created with due_date=NULL (eng review #14)

**Backend integration tests (`test_reminders_sync_engine.py`):**
- Pull: new VTODOs create Tasks + List, existing VTODOs update, deleted VTODOs removed
- Push: PENDING_PUSH task → VTODO created/updated on iCloud
- **Completion round-trip:** complete in app → push → pull → verify still complete
- **Subtask parent resolution:** two-pass sync correctly links parent_id from RELATED-TO
- **Conflict resolution:** local edit + remote edit → last-write-wins
- **Disconnect cleanup:** removing reminders clears sync metadata on tasks, tasks remain as local (eng review #14)
- **Duplicate external_id race:** concurrent sync doesn't crash — upsert or UniqueViolation handled (eng review #14)
- **Push exhaustion:** 3 retries fail → task stays PENDING_PUSH, no data corruption (eng review #14)

**Backend integration tests (`test_integrations_api.py`):**
- `validate-reminders` with existing integration (credential reuse, no password)
- `connect-reminders` creates Calendar rows with `is_todo=True`
- `disconnect-reminders` removes reminder Calendar rows + clears task sync metadata
- **Synced list delete blocked:** DELETE /lists/{id} returns 400 with message (eng review #14)

**Frontend tests:**
- ReminderListSelector: checkbox list, task counts, select/deselect
- iCloud badge rendering on ListPanel and TaskItem
- Synced list deletion blocked with message

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Apple Reminders sections use proprietary X-APPLE headers | Phase 1 builds sections as local-only. Phase 2 ignores section grouping from iCloud — tasks land unsectioned. Add mapping later if Apple metadata is discoverable. |
| Subtask parent not yet synced when child arrives | Two-pass sync: create all tasks first, resolve parent_external_id → parent_id in second pass |
| `important` → `priority` is a breaking change | Single migration converts data. All schema/CRUD/route/frontend refs updated in same PR. |
| Large reminder lists (no date windowing) | Fetch only incomplete + completed in last 30 days. Batch process if needed. |
| Synced list accidentally deleted from Lists UI | Block deletion of synced lists; direct to Settings > Disconnect Reminders. |

---

## Documentation Updates (both phases)

**File:** `.claude/PRD.md`
- Add feature spec for Task model changes (priority, subtasks, sections) under Section 5.1
- Add feature spec for iCloud Reminders Sync as Section 5.13
- Update roadmap v1.2: mark "iCloud Reminders sync" as "In Progress"
- Update data model (Section 8) with new Task fields, Section entity, List sync fields

**File:** `.claude/IMPLEMENTATION_PLAN.md`
- Add Phase 1.6: Task Model Enhancement (priority, subtasks, sections)
- Add Phase 1.7: iCloud Reminders Two-Way Sync
- Update "Current State" table with new feature statuses

**File:** `.claude/BACKEND_STRUCTURE.md`
- Update Task, List, Section table definitions
- Add Section API endpoints
- Add Reminders integration endpoints
- Update CalendarIntegration with reminders_status columns

**TODOs tracked in `.claude/TODOS.md`:**
1. Rename CalendarIntegration → CloudIntegration (P3, S, after Phase 2)
2. Stuck PENDING_PUSH recovery for calendar + reminders sync (P2, S, anytime)
3. Drag-and-drop reorder for sections and tasks (P3, M, after Phase 1)

---

## Verification

### Phase 1
1. Run backend tests: `docker-compose exec api uv run pytest -v`
2. Run frontend tests: `docker-compose exec frontend npm run test:run`
3. Manual: Create tasks with priority, add subtasks, create/edit/delete sections
4. Verify migration handles existing `important` data correctly

### Phase 2
1. Run all backend tests including new sync engine tests
2. Run all frontend tests including new settings UI tests
3. Manual: Connect iCloud Reminders from Settings, verify lists/tasks appear, toggle completion both ways, delete sync, verify cleanup
4. Verify Celery beat triggers periodic reminders sync

---

## Critical Files

**Phase 1 modifies:**
- `backend/app/models.py` — Task, List, new Section
- `backend/app/schemas.py` — Task/List schemas, new Section schemas
- `backend/app/crud_tasks.py` — load-modify-save refactor, priority/parent_id/section_id/completed_at, cycle detection, cross-list validation, default limit fix
- `backend/app/routes/tasks.py` — thin routes (push triggers moved to CRUD)
- `frontend/src/components/lists/TaskItem.jsx` — priority indicator, subtask nesting
- `frontend/src/components/lists/TodoForm.jsx` — priority selector, parent_id
- `frontend/src/components/lists/TaskListView.jsx` — section grouping, subtask filtering
- `frontend/src/pages/ListsPage.jsx` — section CRUD, data flow

**Phase 1 creates:**
- `backend/alembic/versions/<gen>_add_priority_subtasks_sections_sync_metadata.py`
- `backend/app/crud_sections.py`
- `backend/app/routes/sections.py`
- `frontend/src/components/lists/SectionHeader.jsx`

**Phase 2 modifies:**
- `backend/app/services/caldav_client.py` — VTODO functions
- `backend/app/tasks.py` — reminders Celery tasks
- `backend/app/celery_app.py` — beat schedule
- `backend/app/routes/integrations.py` — validate-reminders, connect-reminders endpoints
- `backend/app/crud_tasks.py` — CRUD-level push triggers for synced tasks
- `backend/app/crud_calendar_events.py` — refactor: push triggers moved from routes (eng review #10)
- `backend/app/routes/calendar_events.py` — thin down: push triggers moved to CRUD (eng review #10)
- `backend/app/crud_lists.py` — block synced list deletion
- `frontend/src/components/settings/ICloudSettings.jsx` — Reminders section in card
- `frontend/src/components/lists/ListPanel.jsx` — iCloud badge
- `frontend/src/components/lists/TaskItem.jsx` — iCloud badge

**Phase 2 creates:**
- `backend/app/services/sync_base.py` — shared sync helpers (refactored from sync_engine.py)
- `backend/app/services/reminders_sync_engine.py`
- `frontend/src/components/settings/ReminderListSelector.jsx`

---

## NOT in Scope

| Item | Rationale |
|------|-----------|
| Rename CalendarIntegration → CloudIntegration | High blast radius, zero functional value. Follow-up PR after Phase 2. |
| Apple Reminders sections sync from iCloud | Proprietary X-APPLE headers, undocumented. Sections are local-only in Phase 1. |
| Real-time push notifications (webhook/push) | Requires Apple Push infrastructure. Polling (10-min) is adequate for v1. |
| Google Tasks integration | Different protocol (REST API, OAuth). Future work, but `is_todo` flag prepares for it. |
| Drag-and-drop reorder for sections/tasks | UX enhancement, not required for sync functionality. Follow-up. |
| Stuck PENDING_PUSH recovery mechanism | Existing tech debt (affects calendar sync too). Separate fix. |

## What Already Exists (reused)

| Existing code | How it's reused |
|--------------|-----------------|
| `caldav_client.connect_icloud()` | Same connection for VTODOs |
| `CalendarIntegration` model + `encryption.py` | Shared credentials, no re-login |
| `sync_engine.py` pull/push/conflict pattern | Extracted to `sync_base.py`, both engines import |
| `tasks.py` Celery `run_async()` bridge | Same pattern for new Celery tasks |
| `Calendar` model + `crud_calendars.py` | Reused with `is_todo=True` for reminder lists |
| `ICloudSettings.jsx` + `CalendarSelector.jsx` | Extended UI, `ReminderListSelector` follows same pattern |
| `celery_app.py` beat schedule | Extended with reminders sync entry |

## Dream State Delta

This plan delivers ~70% of the 12-month ideal for task sync:
- Two-way Apple Reminders sync (complete)
- Subtask nesting (complete)
- Sections (local-only, iCloud mapping deferred)
- Priority alignment (complete)

Remaining for ideal state: Google Tasks, real-time push, cross-device instant sync, smart notifications.
