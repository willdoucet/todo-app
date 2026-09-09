# iCloud Reminders Plan — Summary

## Phase 1: Task Model Enhancement + UI

### Step 1.1: Alembic Migration — [✓]
- Migration: `4d4afd73e72a_add_priority_subtasks_sections_sync_.py`
- Data migration: `important=True` → `priority=1`

### Step 1.2: Update SQLAlchemy Models — [✓]
- Task, Section, List, Calendar, CalendarIntegration updated

### Step 1.3: Update Pydantic Schemas — [✓]
- Task, List, Section schemas updated with computed is_synced

### Step 1.4: CRUD Updates — [✓]
- crud_tasks.py refactored, crud_sections.py created, crud_lists.py updated

### Step 1.5: Section API Routes — [✓]
- routes/sections.py created, registered in main.py

### Step 1.6: Frontend — Priority Replaces Important — [✓]
- TaskItem.jsx: PriorityFlag component, TodoForm.jsx: priority selector

### Step 1.7: Frontend — Sections UI — [✓]
- SectionHeader.jsx, TaskListView.jsx, ListsPage.jsx updated

### Step 1.8: Frontend — Subtasks UI — [✓]
- Recursive TaskTree, expand/collapse, depth-based indentation

### Phase 1 Testing — [✓]
- Frontend: 321 passing, Backend: 299 passing

---

## Phase 2: iCloud Reminders Sync Engine

### Step 2.1: CalDAV VTODO Client Functions — [✓]
- Added to `backend/app/services/caldav_client.py`:
  - `list_reminder_lists`, `fetch_todos`, `vtodo_to_task_data`, `task_data_to_vtodo`
  - `create_remote_todo`, `update_remote_todo`, `delete_remote_todo`
- Priority mapping: iCal 1-4→1(high), 5→5(med), 6-9→9(low), 0→0(none)

### Step 2.2: Extract Shared Sync Base + Reminders Sync Engine — [✓]
- Created `backend/app/services/sync_base.py`:
  - `load_integration_with_credentials`, `update_sync_status`, `get_calendar_rows`
- Created `backend/app/services/reminders_sync_engine.py`:
  - `pull_reminders_from_icloud` with two-pass parent resolution
  - `push_task_to_icloud`, `push_task_delete_to_icloud`
  - Auto-creates List for each synced reminder list
  - Last-write-wins conflict resolution

### Step 2.3: Add `is_todo` to Calendar Model — [✓]
- Already done in Phase 1 migration

### Step 2.4: Integration Routes for Reminders — [✓]
- Added to `backend/app/routes/integrations.py`:
  - `POST /integrations/icloud/validate-reminders` — credential reuse
  - `POST /integrations/icloud/connect-reminders` — creates Calendar rows (is_todo=True)
  - `POST /integrations/{id}/sync-reminders` — manual sync
  - `DELETE /integrations/{id}/reminders` — disconnect (keeps tasks/lists local)
- Added schemas: `ICloudReminderListInfo`, `RemindersConnectPayload`
- Extended `CalendarIntegrationResponse` with reminders_status fields and reminder_lists

### Step 2.5: Celery Tasks for Reminders — [✓]
- Added to `backend/app/tasks.py`:
  - `sync_all_reminders` — periodic (10 min)
  - `sync_single_reminders_integration` — initial + manual
  - `push_task_to_icloud_task` — push VTODO changes
  - `push_task_delete_to_icloud_task` — push VTODO deletion
- Added to `backend/app/celery_app.py`:
  - `sync-icloud-reminders` beat schedule entry (600s)

### Step 2.6: CRUD-Level Push Triggers — [✓]
- `crud_tasks.py`: update_task sets PENDING_PUSH + dispatches push for synced tasks
- `crud_tasks.py`: delete_task dispatches push_delete for synced tasks
- Note: Calendar events push trigger refactor (moving from routes to CRUD) deferred — existing code works

### Step 2.7: Frontend — Extend ICloudSettings — [✓]
- Created `frontend/src/components/settings/ReminderListSelector.jsx`
- Extended `IntegrationCard` in `ICloudSettings.jsx`:
  - Calendar status (top half) + Reminders status (bottom half)
  - "Connect Reminders" flow: validate → select lists → connect
  - Separate status badges, sync now, disconnect for reminders

### Step 2.8: Frontend — iCloud Badges — [✓]
- `ListPanel.jsx`: cloud icon for synced lists, delete button hidden for synced lists
- `TaskItem.jsx`: cloud icon for synced tasks, "Syncing..." for PENDING_PUSH

---

## Completion
- **Phase 1 Timestamp:** 2026-03-25
- **Phase 2 Timestamp:** 2026-03-25
- **Verification Timestamp:** 2026-03-25
- **All steps:** [✓] Complete

### Test Results (verified)
- Frontend: 321 tests passing (27 test files)
- Backend: 325 passed, 1 pre-existing failure (unrelated calendar event validation)

### Summary of What Was Built
**Phase 1** evolved the Task model for Apple Reminders alignment:
- Priority system (0=none, 1=high, 5=medium, 9=low)
- Subtasks with cycle detection
- Sections with CRUD API
- Sync metadata on tasks/lists
- Frontend: priority flags, sections, subtask tree

**Phase 2** added two-way iCloud Reminders sync:
- CalDAV VTODO protocol support (full CRUD)
- Pull engine with two-pass parent resolution for subtasks
- Push engine for task edits/deletes
- Celery tasks with periodic sync (10 min)
- CRUD-level push triggers for synced tasks
- Settings UI: connect/disconnect reminders, separate status badges
- List/task badges: cloud icon, synced list delete prevention

### Verification Fixes
- Added 26 VTODO unit tests (`test_vtodo_client.py`)
- Refactored `sync_engine.py` to import constants from `sync_base.py`
- Updated `IMPLEMENTATION_PLAN.md` with new features and test counts

### Files Created (Phase 2)
- `backend/app/services/sync_base.py`
- `backend/app/services/reminders_sync_engine.py`
- `backend/tests/unit/test_vtodo_client.py`
- `frontend/src/components/settings/ReminderListSelector.jsx`

### Files Modified (Phase 2)
- `backend/app/services/caldav_client.py` — VTODO functions
- `backend/app/services/sync_engine.py` — imports from sync_base.py
- `backend/app/schemas.py` — reminders schemas, extended integration response
- `backend/app/routes/integrations.py` — 4 reminders endpoints
- `backend/app/tasks.py` — 4 reminders Celery tasks
- `backend/app/celery_app.py` — beat schedule
- `backend/app/crud_tasks.py` — push triggers, timezone fix
- `frontend/src/components/settings/ICloudSettings.jsx` — reminders section
- `frontend/src/components/lists/ListPanel.jsx` — cloud badges
- `frontend/src/components/lists/TaskItem.jsx` — cloud badges

### Deferred Items (noted in plan as acceptable)
1. **Calendar events push trigger refactor** (eng review #10): Moving push triggers from `routes/calendar_events.py` to `crud_calendar_events.py` — existing code works, refactor is a consistency improvement
2. **Integration tests for reminders sync engine**: Would require mocking CalDAV server (same pattern as existing calendar sync tests which also don't exist). Unit tests cover the mapping logic.
3. **Frontend component tests for ReminderListSelector/badges**: Follow same pattern as CalendarSelector tests; low risk as they follow established patterns
