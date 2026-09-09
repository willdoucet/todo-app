# iCloud Calendar Integration - Implementation Plan

> **Feature**: Two-way iCloud Calendar sync via CalDAV + Celery background workers

---

## Context

The calendar dashboard is complete (18 components, click-to-edit, 274 frontend tests, 18 backend integration tests). The `CalendarEvent` model already has `source` (MANUAL/ICLOUD/GOOGLE) and `external_id` fields. This plan adds the full iCloud sync pipeline: CalDAV connection via app-specific passwords, periodic two-way sync via Celery+Redis, and a Settings UI for managing integrations.

**No authentication exists yet.** Integrations are linked to FamilyMember. Auth will be retrofitted later with minimal rework (~1-2 hours of adding auth guards to integration endpoints).

---

## Design Decisions (from user)

| Decision | Choice |
|----------|--------|
| Task queue | Celery + Redis (learning goal + future AI recipe feature) |
| Auth method | CalDAV + app-specific passwords (not Apple Sign-In) |
| Auth dependency | Skip for now, link CalendarIntegration to FamilyMember |
| Encryption | Fernet, secret key in `FERNET_KEY` env var |
| Two-way sync | Yes — remove MANUAL-only edit restriction for ICLOUD events |
| Sync metadata | Extra columns on CalendarEvent (not separate table) |
| Unique constraint | `UNIQUE(external_id, calendar_integration_id)` |
| Multiple accounts | Yes, per-family-member, user chooses which calendars |
| Recurring events | Skip for v1 (filter out during sync) |
| Conflict resolution | UTC conversion, last-write-wins, log conflicts |
| Sync range | 30 days past / 90 days future (configurable, keep aged-out events) |
| Sync frequency | Every 10 minutes via Celery Beat |
| Push timing | Dedicated Celery task fires within ~30 seconds of local edit |
| Delete behavior | Push deletes to iCloud with confirmation dialog in UI |
| Disconnect behavior | Delete all synced events from Family Hub |
| Calendar selection | During initial connection flow, with shared calendar duplicate warning |
| Settings UI | Integrations section below Family Members on Settings page |
| Synced event editing | Visual "Synced from iCloud" indicator + warning before save |
| Manual sync | "Sync Now" button alongside periodic sync |
| Initial sync | Celery task with "Syncing..." status indicator |
| Error handling | Error banner on Settings page, stop syncing until credentials fixed |
| Reassign synced events | Yes — `assigned_to` is local-only, preserved across syncs |
| Testing | Unit tests with mocked CalDAV (CI) + manual playbook + optional smoke test |

---

## New Dependencies

### Backend (pyproject.toml)

| Package | Purpose |
|---------|---------|
| `celery[redis]` | Task queue with Redis broker |
| `redis` | Redis client for direct status checks |
| `caldav` | CalDAV protocol client |
| `icalendar` | ICS parsing/generation |
| `cryptography` | Fernet symmetric encryption |

### Infrastructure (docker-compose.yml)

| Service | Image | Purpose |
|---------|-------|---------|
| `redis` | `redis:7-alpine` | Message broker + result backend |
| `celery_worker` | Same as `api` (dev target) | Runs Celery worker process |
| `celery_beat` | Same as `api` (dev target) | Runs Celery Beat scheduler |

---

## File Map

### New Files

| File | Purpose |
|------|---------|
| `backend/app/celery_app.py` | Celery app instance + config |
| `backend/app/tasks.py` | Celery task definitions (sync, push, initial sync) |
| `backend/app/utils/encryption.py` | Fernet encrypt/decrypt helpers |
| `backend/app/utils/__init__.py` | Package init |
| `backend/app/services/caldav_client.py` | CalDAV connection, calendar listing, event CRUD |
| `backend/app/services/sync_engine.py` | Pull/push sync logic, conflict resolution |
| `backend/app/services/__init__.py` | Package init |
| `backend/app/crud_calendar_integrations.py` | CRUD for CalendarIntegration |
| `backend/app/routes/integrations.py` | API endpoints for connect/disconnect/sync/status |
| `frontend/src/components/settings/ICloudSettings.jsx` | Connection form, status, calendar selector |
| `frontend/src/components/settings/CalendarSelector.jsx` | Checkbox list of available calendars |

### Modified Files

| File | Change |
|------|--------|
| `backend/app/models.py` | Add `CalendarIntegration` model, add sync columns to `CalendarEvent` |
| `backend/app/schemas.py` | Add integration schemas, update CalendarEvent schemas |
| `backend/app/routes/calendar_events.py` | Allow editing/deleting ICLOUD events (remove source restriction) |
| `backend/app/main.py` | Register integrations router |
| `backend/docker-compose.yml` | Add redis, celery_worker, celery_beat services |
| `backend/Dockerfile` | No change needed (deps installed via pyproject.toml) |
| `backend/pyproject.toml` | Add new dependencies |
| `frontend/src/pages/FamilyMembersPage.jsx` | Add Integrations section below Family Members |
| `frontend/src/components/calendar/EventFormModal.jsx` | Add sync indicator + edit warning |

### New Alembic Migrations

| Migration | Changes |
|-----------|---------|
| `add_calendar_integration_table` | New `calendar_integrations` table |
| `add_sync_columns_to_calendar_events` | Add `etag`, `last_modified_remote`, `sync_status`, `calendar_integration_id` to `calendar_events`; drop old `UNIQUE(external_id)`, add `UNIQUE(external_id, calendar_integration_id)` |

---

## Phase 1: Infrastructure — Celery + Redis

**Goal**: Celery worker + beat running in Docker, verified with a health-check task.

### 1A. Add dependencies to pyproject.toml

**File**: `backend/pyproject.toml`

Add to `dependencies`:
```
"celery[redis]>=5.4",
"redis>=5.0",
"caldav>=1.4",
"icalendar>=6.0",
"cryptography>=43.0",
```

Then rebuild: `docker-compose build api`

### 1B. Create Celery app

**File**: `backend/app/celery_app.py`

```python
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "family_hub",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "sync-icloud-calendars": {
            "task": "app.tasks.sync_all_icloud_integrations",
            "schedule": 600.0,  # Every 10 minutes
        },
    },
)
```

### 1C. Create placeholder tasks

**File**: `backend/app/tasks.py`

```python
import logging
from .celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.health_check")
def health_check():
    """Simple task to verify Celery is working."""
    logger.info("Celery health check: OK")
    return {"status": "ok"}

@celery_app.task(name="app.tasks.sync_all_icloud_integrations")
def sync_all_icloud_integrations():
    """Placeholder — will sync all active iCloud integrations."""
    logger.info("sync_all_icloud_integrations: not yet implemented")
    return {"status": "not_implemented"}
```

### 1D. Update docker-compose.yml

**File**: `backend/docker-compose.yml`

Add three new services:

```yaml
  redis:
    image: redis:7-alpine
    restart: always
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  celery_worker:
    build:
      context: .
      target: dev
    restart: unless-stopped
    command: celery -A app.celery_app worker --loglevel=info --concurrency=2
    volumes:
      - ./app:/app/app:ro
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - FERNET_KEY=${FERNET_KEY}
      - PYTHONUNBUFFERED=1
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    env_file:
      - .env

  celery_beat:
    build:
      context: .
      target: dev
    restart: unless-stopped
    command: celery -A app.celery_app beat --loglevel=info
    volumes:
      - ./app:/app/app:ro
    environment:
      - REDIS_URL=redis://redis:6379/0
      - PYTHONUNBUFFERED=1
    depends_on:
      redis:
        condition: service_healthy
    env_file:
      - .env
```

Add `REDIS_URL` and `FERNET_KEY` to the `api` service environment too. Add `FERNET_KEY` to `.env`.

### 1E. Verify

- `docker-compose up --build`
- `docker-compose exec celery_worker celery -A app.celery_app inspect ping` → should respond
- `docker-compose exec api python -c "from app.tasks import health_check; r = health_check.delay(); print(r.get(timeout=5))"` → should print `{'status': 'ok'}`

---

## Phase 2: Data Model

**Goal**: CalendarIntegration table + sync columns on CalendarEvent, with migrations.

### 2A. Add CalendarIntegration model

**File**: `backend/app/models.py`

New enum:
```python
class IntegrationStatus(PyEnum):
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    SYNCING = "SYNCING"
    DISCONNECTED = "DISCONNECTED"
```

New model:
```python
class CalendarIntegration(Base):
    __tablename__ = "calendar_integrations"

    id = Column(Integer, primary_key=True, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=False)
    provider = Column(String, nullable=False, default="icloud")  # "icloud" or "google" later
    email = Column(String, nullable=False)
    encrypted_password = Column(String, nullable=False)  # Fernet-encrypted app-specific password
    status = Column(
        SQLEnum(IntegrationStatus),
        default=IntegrationStatus.ACTIVE,
        nullable=False,
    )
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    sync_range_past_days = Column(Integer, default=30)
    sync_range_future_days = Column(Integer, default=90)
    selected_calendars = Column(JSON, nullable=True)  # Array of calendar URLs/IDs to sync

    family_member = relationship("FamilyMember")
    calendar_events = relationship("CalendarEvent", back_populates="integration")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
```

### 2B. Add sync columns to CalendarEvent

**File**: `backend/app/models.py`

Add to `CalendarEvent`:
```python
    etag = Column(String, nullable=True)  # CalDAV ETag for change detection
    last_modified_remote = Column(DateTime, nullable=True)  # Remote LAST-MODIFIED in UTC
    sync_status = Column(String, nullable=True)  # SYNCED, PENDING_PUSH, CONFLICT
    calendar_integration_id = Column(
        Integer,
        ForeignKey("calendar_integrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    integration = relationship("CalendarIntegration", back_populates="calendar_events")
```

Update `__table_args__` to replace the unique constraint:
```python
    __table_args__ = (
        UniqueConstraint(
            "external_id",
            "calendar_integration_id",
            name="uq_calendar_event_external_integration",
        ),
    )
```

### 2C. Add relationship to FamilyMember

**File**: `backend/app/models.py`

Add to `FamilyMember`:
```python
    calendar_integrations = relationship("CalendarIntegration", back_populates="family_member")
```

### 2D. Add schemas

**File**: `backend/app/schemas.py`

```python
# =============================================================================
# CalendarIntegration Schemas
# =============================================================================

class IntegrationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    SYNCING = "SYNCING"
    DISCONNECTED = "DISCONNECTED"

class CalendarIntegrationCreate(BaseModel):
    family_member_id: int = Field(..., ge=1)
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)  # Plain text — encrypted before storage
    selected_calendars: Optional[TypingList[str]] = None

class CalendarIntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_member_id: int
    provider: str
    email: str
    # NOTE: password is NEVER returned
    status: IntegrationStatus
    last_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
    sync_range_past_days: int
    sync_range_future_days: int
    selected_calendars: Optional[TypingList[str]] = None
    family_member: FamilyMember
    created_at: datetime
    updated_at: Optional[datetime] = None

class ICloudCalendarInfo(BaseModel):
    """Returned when listing available calendars from an iCloud account."""
    url: str
    name: str
    color: Optional[str] = None
    event_count: Optional[int] = None
    already_synced_by: Optional[str] = None  # Family member name if already synced
```

Update `CalendarEvent` response schema to include new fields:
```python
class CalendarEvent(CalendarEventBase):
    # ... existing fields ...
    sync_status: Optional[str] = None
    calendar_integration_id: Optional[int] = None
```

### 2E. Create Alembic migrations

Two migrations in sequence:

**Migration 1**: `add_calendar_integration_table`
- Create `calendar_integrations` table with all columns
- Add `IntegrationStatus` enum type

**Migration 2**: `add_sync_columns_to_calendar_events`
- Add `etag`, `last_modified_remote`, `sync_status`, `calendar_integration_id` columns
- Drop existing `UNIQUE` index on `external_id`
- Add `UNIQUE(external_id, calendar_integration_id)` constraint

### 2F. Create CRUD

**File**: `backend/app/crud_calendar_integrations.py`

Standard CRUD following existing pattern:
- `get_integrations(db, family_member_id=None)` — list all or filter by member
- `get_integration(db, integration_id)` — single by ID
- `get_active_integrations(db)` — all with status=ACTIVE (for Celery beat)
- `create_integration(db, integration)` — create with encrypted password
- `update_integration_status(db, integration_id, status, last_error=None)` — update status/error
- `update_integration_last_sync(db, integration_id)` — update last_sync_at
- `delete_integration(db, integration_id)` — delete + cascade delete synced events

### 2G. Verify

- Run migrations: `docker-compose exec api alembic upgrade head`
- Verify tables: `docker-compose exec db psql -U postgres -d todo_app -c "\dt"` shows `calendar_integrations`
- Verify columns: `docker-compose exec db psql -U postgres -d todo_app -c "\d calendar_events"` shows new columns

---

## Phase 3: Encryption Utilities

**Goal**: Fernet encrypt/decrypt for app-specific passwords. Never log plaintext.

### 3A. Create encryption module

**File**: `backend/app/utils/encryption.py`

```python
import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

def _get_fernet() -> Fernet:
    key = os.getenv("FERNET_KEY")
    if not key:
        raise RuntimeError("FERNET_KEY environment variable is not set")
    return Fernet(key.encode())

def encrypt_password(plain_text: str) -> str:
    """Encrypt a password string. Returns base64-encoded ciphertext."""
    return _get_fernet().encrypt(plain_text.encode()).decode()

def decrypt_password(encrypted: str) -> str:
    """Decrypt a password string. Raises RuntimeError on failure."""
    try:
        return _get_fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt password — FERNET_KEY may have changed")
        raise RuntimeError("Failed to decrypt stored credentials")
```

### 3B. Generate Fernet key

Add to `.env`:
```
FERNET_KEY=<generated-key>
```

Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### 3C. Verify

Unit test: encrypt a value → decrypt → assert equal. Attempt decrypt with wrong key → assert raises.

---

## Phase 4: CalDAV Client

**Goal**: Wrapper around the `caldav` library for iCloud-specific operations.

### 4A. Create CalDAV client

**File**: `backend/app/services/caldav_client.py`

Key functions:

```python
def connect_icloud(email: str, password: str) -> caldav.DAVClient:
    """Connect to iCloud CalDAV. Raises on auth failure."""
    # iCloud CalDAV URL: https://caldav.icloud.com
    client = caldav.DAVClient(
        url="https://caldav.icloud.com",
        username=email,
        password=password,
    )
    principal = client.principal()  # Validates credentials
    return client, principal

def list_calendars(principal) -> list[dict]:
    """List available calendars from iCloud account.
    Returns: [{"url": str, "name": str, "color": str|None}]
    """

def fetch_events(calendar, start_date, end_date) -> list[icalendar.Calendar]:
    """Fetch all events from a calendar within date range.
    Filters out recurring events (v1: single events only).
    Returns parsed iCalendar objects.
    """

def create_remote_event(calendar, event_data: dict) -> str:
    """Create event on iCloud. Returns the UID."""

def update_remote_event(calendar, uid: str, event_data: dict) -> None:
    """Update event on iCloud by UID."""

def delete_remote_event(calendar, uid: str) -> None:
    """Delete event from iCloud by UID."""
```

**iCloud-specific notes:**
- CalDAV URL: `https://caldav.icloud.com`
- Auth: HTTP Basic with email + app-specific password
- The `caldav` library is synchronous — this is fine for Celery workers (sync tasks run in Celery's process pool, not in the async FastAPI event loop)
- For the "Sync Now" API endpoint, we'll dispatch to Celery rather than calling CalDAV synchronously in FastAPI

### 4B. ICS ↔ CalendarEvent mapping

**File**: `backend/app/services/caldav_client.py` (continued)

```python
def ics_to_event_data(vevent) -> dict:
    """Convert an iCalendar VEVENT to a dict matching CalendarEventCreate fields.

    Mapping:
    - SUMMARY → title
    - DESCRIPTION → description
    - DTSTART → date + start_time (convert to UTC, extract date and HH:MM)
    - DTEND → end_time
    - UID → external_id
    - LAST-MODIFIED → last_modified_remote (UTC)
    - All-day: DTSTART is a date (not datetime)
    """

def event_data_to_ics(event: dict) -> icalendar.Calendar:
    """Convert CalendarEvent fields to an iCalendar object for pushing to iCloud.

    Reverse of ics_to_event_data.
    """
```

**Recurring event handling**: If `RRULE` property is present on a VEVENT, skip it (log a debug message). Only sync single-occurrence events for v1.

---

## Phase 5: Sync Engine

**Goal**: Core pull/push logic with conflict resolution.

### 5A. Create sync engine

**File**: `backend/app/services/sync_engine.py`

```python
async def pull_from_icloud(integration_id: int) -> dict:
    """Pull events from iCloud into local DB.

    Steps:
    1. Load CalendarIntegration (decrypt password)
    2. Connect to iCloud via CalDAV
    3. For each selected calendar:
       a. Fetch events in sync range (past N days → future M days)
       b. For each event:
          - If external_id exists locally: compare last_modified_remote
            - Remote is newer → update local fields (title, desc, date, times)
              BUT preserve assigned_to (local-only field)
            - Local is newer → skip (will be pushed)
            - Equal → skip
          - If external_id not found locally: create new CalendarEvent
            (source=ICLOUD, assigned_to=integration.family_member_id)
       c. For local ICLOUD events in this integration that are NOT in the
          remote fetch: mark as deleted (remote deletion detected)
    4. Update integration.last_sync_at
    5. Return summary: {created: N, updated: N, deleted: N, conflicts: N}

    Conflict logging:
    - When both sides changed, log to logger.warning with event details
    - Apply last-write-wins (compare last_modified_remote UTC vs updated_at UTC)
    """

async def push_to_icloud(event_id: int) -> dict:
    """Push a single local change to iCloud.

    Steps:
    1. Load CalendarEvent + its CalendarIntegration
    2. Decrypt password, connect to iCloud
    3. Find the calendar URL from integration.selected_calendars
    4. If sync_status == PENDING_PUSH:
       - If external_id exists on remote: update remote event
       - If external_id is None (newly created locally): create on remote, save external_id
    5. If event was deleted locally: delete on remote
    6. Set sync_status = SYNCED
    7. Return {action: "updated"|"created"|"deleted"}

    Error handling:
    - If CalDAV call fails, keep sync_status as PENDING_PUSH
    - Celery retry with exponential backoff (max 3 retries)
    """

async def push_delete_to_icloud(external_id: str, integration_id: int) -> dict:
    """Push a delete to iCloud when user deletes a synced event locally.

    Separate function because the local event is already gone.
    """
```

### 5B. Sync status flow

```
New event synced from iCloud    → sync_status = SYNCED
User edits ICLOUD event locally → sync_status = PENDING_PUSH
Push task runs successfully     → sync_status = SYNCED
Pull finds remote is newer      → sync_status = SYNCED (overwritten)
Both changed (conflict)         → last-write-wins, log conflict, sync_status = SYNCED
```

### 5C. Preserving local-only fields during pull

When updating a local event from remote data, the sync engine must **never overwrite**:
- `assigned_to` — local-only assignment, not part of iCloud
- `calendar_integration_id` — set once at creation
- `id`, `created_at` — immutable

Fields that ARE updated from remote:
- `title`, `description`, `date`, `start_time`, `end_time`, `all_day`
- `etag`, `last_modified_remote`

---

## Phase 6: Celery Tasks

**Goal**: Wire sync engine into Celery tasks.

### 6A. Implement tasks

**File**: `backend/app/tasks.py`

```python
@celery_app.task(name="app.tasks.sync_all_icloud_integrations")
def sync_all_icloud_integrations():
    """Periodic task (every 10 min): sync all active iCloud integrations.

    Runs pull_from_icloud for each integration with status=ACTIVE.
    On auth failure, sets integration status to ERROR.
    """

@celery_app.task(
    name="app.tasks.sync_single_integration",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def sync_single_integration(self, integration_id: int):
    """Sync a single integration. Used for initial sync + manual 'Sync Now'.

    Sets integration status to SYNCING during execution.
    On success: status → ACTIVE
    On auth error: status → ERROR, last_error set
    On other error: retry with backoff
    """

@celery_app.task(
    name="app.tasks.push_event_to_icloud",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def push_event_to_icloud(self, event_id: int):
    """Push a single event change to iCloud (~30 second delay via countdown).

    Called when user edits/creates an ICLOUD event locally.
    On failure: retry with exponential backoff (10s, 20s, 40s).
    """

@celery_app.task(name="app.tasks.push_delete_to_icloud")
def push_delete_to_icloud(external_id: str, integration_id: int):
    """Push a delete to iCloud. Called when user deletes a synced event."""

@celery_app.task(name="app.tasks.delete_events_for_integration")
def delete_events_for_integration(integration_id: int):
    """Delete all local events for a disconnected integration."""
```

### 6B. Async ↔ Sync bridge

Celery tasks are synchronous. The sync engine uses async SQLAlchemy. Bridge with:

```python
import asyncio
from .database import AsyncSessionLocal

def run_async(coro):
    """Run an async function from synchronous Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
```

Each task creates its own `AsyncSession` via `AsyncSessionLocal()` — not via FastAPI's `Depends(get_db)`.

### 6C. Triggering push tasks from API

When `PATCH /calendar-events/{id}` is called on an ICLOUD event:
1. Update the local DB (existing behavior)
2. Set `sync_status = PENDING_PUSH`
3. Dispatch `push_event_to_icloud.apply_async(args=[event_id], countdown=30)`

Similarly for `DELETE /calendar-events/{id}` on an ICLOUD event:
1. Save `external_id` and `calendar_integration_id` before deleting
2. Delete local event
3. Dispatch `push_delete_to_icloud.apply_async(args=[external_id, integration_id], countdown=30)`

---

## Phase 7: API Endpoints

**Goal**: REST endpoints for managing iCloud integrations.

### 7A. Create integrations router

**File**: `backend/app/routes/integrations.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/integrations/icloud/validate` | Validate credentials + return available calendars (step 1 of connection flow) |
| `POST` | `/integrations/icloud/connect` | Store credentials + selected calendars, trigger initial sync |
| `GET` | `/integrations/calendars` | List all connected integrations (all providers) |
| `GET` | `/integrations/{id}` | Get single integration status |
| `POST` | `/integrations/{id}/sync` | Trigger manual "Sync Now" (dispatches Celery task) |
| `DELETE` | `/integrations/{id}` | Disconnect: delete integration + all its synced events |

**Connection flow (2-step):**

1. `POST /integrations/icloud/validate`
   - Request: `{ email, password, family_member_id }`
   - Connects to iCloud CalDAV to validate credentials
   - Fetches calendar list
   - For each calendar, checks if any event UIDs already exist locally (shared calendar detection)
   - Returns: `{ calendars: [{ url, name, color, event_count, already_synced_by }] }`
   - Does NOT store credentials yet

2. `POST /integrations/icloud/connect`
   - Request: `{ email, password, family_member_id, selected_calendars: [url1, url2] }`
   - Encrypts password, creates CalendarIntegration row
   - Dispatches `sync_single_integration.delay(integration_id)` for initial sync
   - Returns: `CalendarIntegrationResponse` with `status: SYNCING`

### 7B. Modify calendar events routes

**File**: `backend/app/routes/calendar_events.py`

Remove the MANUAL-only restriction for ICLOUD events on PATCH and DELETE:

**PATCH** — allow editing ICLOUD events:
```python
@router.patch("/{event_id}", response_model=schemas.CalendarEvent)
async def update_calendar_event(...):
    existing = await crud_calendar_events.get_calendar_event(db, event_id)
    if existing is None:
        raise HTTPException(status_code=404)
    if existing.source == CalendarEventSource.GOOGLE:
        raise HTTPException(status_code=400, detail="Google Calendar events cannot be edited yet")
    # ICLOUD events: update locally + queue push
    result = await crud_calendar_events.update_calendar_event(db, event_id, event_update)
    if existing.source == CalendarEventSource.ICLOUD:
        # Set sync_status and dispatch push task
        await crud_calendar_events.set_sync_status(db, event_id, "PENDING_PUSH")
        from ..tasks import push_event_to_icloud
        push_event_to_icloud.apply_async(args=[event_id], countdown=30)
    return result
```

**DELETE** — allow deleting ICLOUD events:
```python
@router.delete("/{event_id}", response_model=schemas.CalendarEvent)
async def delete_calendar_event(...):
    existing = await crud_calendar_events.get_calendar_event(db, event_id)
    if existing is None:
        raise HTTPException(status_code=404)
    if existing.source == CalendarEventSource.GOOGLE:
        raise HTTPException(status_code=400, detail="Google Calendar events cannot be deleted yet")
    # For ICLOUD events: push delete to remote
    if existing.source == CalendarEventSource.ICLOUD and existing.external_id:
        from ..tasks import push_delete_to_icloud
        external_id = existing.external_id
        integration_id = existing.calendar_integration_id
    result = await crud_calendar_events.delete_calendar_event(db, event_id)
    if existing.source == CalendarEventSource.ICLOUD and existing.external_id:
        push_delete_to_icloud.apply_async(
            args=[external_id, integration_id], countdown=30
        )
    return result
```

### 7C. Register router

**File**: `backend/app/main.py`

```python
from .routes import integrations
app.include_router(integrations.router)
```

---

## Phase 8: Frontend

**Goal**: Settings UI for managing iCloud connections + visual indicators on synced events.

### 8A. ICloud Settings Component

**File**: `frontend/src/components/settings/ICloudSettings.jsx`

**States:**
1. **No integrations**: Show "Connect iCloud Calendar" card with form
2. **Connection in progress**: Step 1 (credentials) → Step 2 (calendar selection)
3. **Connected**: Show status card per integration (email, family member, last sync, status)
4. **Error state**: Show error banner with "Check your credentials" message

**Connection Flow UI:**

Step 1 — Enter credentials:
- Family member dropdown (who owns this iCloud account?)
- iCloud email input
- App-specific password input (with link to Apple's help page for generating one)
- "Connect" button → calls `POST /integrations/icloud/validate`

Step 2 — Select calendars:
- List of checkboxes for each calendar (name + color dot + event count)
- Calendars already synced by another family member: shown with warning badge and disabled by default
- "Start Sync" button → calls `POST /integrations/icloud/connect`
- Status changes to "Syncing..." with spinner

**Connected state:**
- Card per integration showing: family member avatar, email, status badge (Active/Syncing/Error)
- "Last synced: X minutes ago"
- "Sync Now" button → calls `POST /integrations/{id}/sync`
- "Disconnect" button → confirmation dialog → calls `DELETE /integrations/{id}`
- Disconnect dialog: "This will delete all events synced from this account. Events will also be removed from iCloud if they were created in Family Hub. Continue?"

### 8B. Calendar Selector Component

**File**: `frontend/src/components/settings/CalendarSelector.jsx`

Presentational component for Step 2 of connection flow:
- Checkbox list of calendars
- Each row: color dot + calendar name + "(N events)" + optional warning badge
- Warning badge: "Already synced from [Name]'s account" (for shared calendars)
- Select All / Deselect All toggle

### 8C. Update Settings Page

**File**: `frontend/src/pages/FamilyMembersPage.jsx`

Add Integrations section below the FamilyMemberManager card:

```jsx
<div className="bg-card-bg dark:bg-gray-800 rounded-xl border border-card-border dark:border-gray-700 p-6 mt-6">
  <h2 className="text-lg font-semibold text-text-primary dark:text-gray-100 mb-4">
    Calendar Integrations
  </h2>
  <ICloudSettings familyMembers={familyMembers} />
</div>
```

Need to fetch family members at the page level so both FamilyMemberManager and ICloudSettings can use them. Or fetch independently in each component (simpler, acceptable duplication for now).

### 8D. Update EventFormModal

**File**: `frontend/src/components/calendar/EventFormModal.jsx`

For events with `source === "ICLOUD"`:

1. **Visual indicator**: Show a badge/chip at the top of the modal:
   ```
   [iCloud icon] Synced from iCloud
   ```
   Use a subtle blue badge matching the iCloud event color.

2. **Edit warning**: When user modifies any field and clicks Save, show confirmation:
   ```
   "This event is synced from iCloud. Your changes will be pushed
   back to iCloud Calendar. Continue?"
   [Cancel] [Save & Sync]
   ```

3. **Delete warning**: When user clicks Delete:
   ```
   "This will also delete the event from iCloud Calendar.
   This action cannot be undone. Continue?"
   [Cancel] [Delete from both]
   ```

4. **Sync status indicator**: If `sync_status === "PENDING_PUSH"`, show a small spinner or "Syncing..." text below the badge.

---

## Phase 9: Testing

### 9A. Unit Tests (mocked CalDAV)

**File**: `backend/tests/unit/test_encryption.py`
- Encrypt/decrypt round-trip
- Decrypt with wrong key raises
- Missing FERNET_KEY raises

**File**: `backend/tests/unit/test_caldav_client.py`
- Mock `caldav.DAVClient` and test `ics_to_event_data` / `event_data_to_ics` mapping
- Test recurring event filtering (RRULE present → skip)
- Test all-day event detection
- Test timezone conversion to UTC

**File**: `backend/tests/unit/test_sync_engine.py`
- Pull: new remote event → creates local event
- Pull: updated remote event (newer) → updates local, preserves assigned_to
- Pull: updated remote event (older) → skips (local is newer)
- Pull: remote event deleted → deletes local event
- Pull: conflict (both changed) → last-write-wins, logged
- Push: local edit → updates remote
- Push: local delete → deletes remote

### 9B. Integration Tests

**File**: `backend/tests/integration/test_integrations_api.py`
- `POST /integrations/icloud/validate` — mock CalDAV, verify calendar list returned
- `POST /integrations/icloud/connect` — verify integration created, password encrypted, Celery task dispatched
- `GET /integrations/calendars` — verify list includes connected integrations
- `DELETE /integrations/{id}` — verify integration + events deleted
- `POST /integrations/{id}/sync` — verify Celery task dispatched

**File**: `backend/tests/integration/test_calendar_events_sync.py`
- `PATCH /calendar-events/{id}` on ICLOUD event → succeeds (was previously 400)
- `DELETE /calendar-events/{id}` on ICLOUD event → succeeds + push task dispatched
- Verify `sync_status` set to `PENDING_PUSH` after edit

### 9C. Frontend Tests

- `ICloudSettings.test.jsx` — render states (no integrations, connected, error)
- `CalendarSelector.test.jsx` — checkbox selection, shared calendar warning
- `EventFormModal.test.jsx` — sync indicator visible for ICLOUD events, edit warning shown

### 9D. Manual Test Playbook

```markdown
## Manual Test: iCloud Calendar Integration

Prerequisites:
- A real iCloud account with an app-specific password
- At least 2-3 events in the next 90 days
- Docker Compose running (`docker-compose up`)

### Connection Flow
1. Go to /settings
2. Click "Connect iCloud Calendar"
3. Select a family member, enter iCloud email + app-specific password
4. Click "Connect" → verify calendar list appears
5. Select one or more calendars → click "Start Sync"
6. Verify "Syncing..." status appears
7. Wait for sync to complete → verify events appear on calendar dashboard

### Two-Way Sync
8. Edit a synced event in Family Hub → verify warning dialog appears
9. Confirm edit → verify change appears on iCloud Calendar (within ~1 min)
10. Edit the same event in iCloud Calendar → wait 10 min → verify change appears in Family Hub

### Delete Sync
11. Delete a synced event in Family Hub → verify warning dialog appears
12. Confirm → verify event disappears from iCloud Calendar

### Disconnect
13. Go to /settings → click "Disconnect" on the integration
14. Confirm → verify all synced events removed from Family Hub calendar

### Error Handling
15. Change the app-specific password in Apple ID settings (revoke old one)
16. Wait for next sync cycle (10 min) → verify error banner appears on Settings page
```

### 9E. Optional Smoke Test

**File**: `backend/tests/integration/test_icloud_smoke.py`

```python
@pytest.mark.skipunless(
    os.getenv("ICLOUD_TEST_EMAIL"),
    "Set ICLOUD_TEST_EMAIL and ICLOUD_TEST_PASSWORD to run"
)
async def test_icloud_connection_smoke():
    """Smoke test: connect to real iCloud and list calendars."""
    client, principal = connect_icloud(
        os.getenv("ICLOUD_TEST_EMAIL"),
        os.getenv("ICLOUD_TEST_PASSWORD"),
    )
    calendars = list_calendars(principal)
    assert len(calendars) > 0
```

---

## Implementation Order

Phases are designed to be independently verifiable:

| Phase | Estimated Effort | Depends On |
|-------|-----------------|------------|
| Phase 1: Celery + Redis Infrastructure | 1 day | Nothing |
| Phase 2: Data Model + Migrations | 1 day | Nothing (parallel with Phase 1) |
| Phase 3: Encryption Utilities | 0.5 day | Nothing (parallel) |
| Phase 4: CalDAV Client | 1-2 days | Phase 3 |
| Phase 5: Sync Engine | 2-3 days | Phase 2, Phase 4 |
| Phase 6: Celery Tasks | 1 day | Phase 1, Phase 5 |
| Phase 7: API Endpoints | 1 day | Phase 2, Phase 6 |
| Phase 8: Frontend | 2-3 days | Phase 7 |
| Phase 9: Testing | 1-2 days | All phases |

**Total: ~10-14 days** for a solo developer, with Phases 1-3 parallelizable.

**Critical path**: Phase 4 (CalDAV) → Phase 5 (Sync Engine) → Phase 6 (Tasks) → Phase 7 (API) → Phase 8 (Frontend)

---

## Environment Variables Added

| Variable | Location | Purpose |
|----------|----------|---------|
| `FERNET_KEY` | `.env` | Fernet encryption key for passwords |
| `REDIS_URL` | `.env` / docker-compose | Redis connection URL (`redis://redis:6379/0`) |

---

## CLAUDE.md Updates Needed After Implementation

- Add redis, celery_worker, celery_beat to Services list
- Add `FERNET_KEY` and `REDIS_URL` to Environment Variables section
- Add `/integrations/*` to API endpoints list
- Update CalendarEvent model documentation with sync columns
- Add CalendarIntegration to Data Model section
- Update docker-compose service count (3 → 6)
- Add Celery commands to Development Commands section:
  - `docker-compose exec celery_worker celery -A app.celery_app inspect ping`
  - `docker-compose logs celery_worker` (for sync debugging)

---

## Risks & Gotchas

| Risk | Mitigation |
|------|-----------|
| iCloud rate limiting | Respect CalDAV `Prefer: return-minimal` header; 10-min sync interval is conservative |
| App-specific password revocation by Apple | Error handling sets integration status to ERROR; user sees banner |
| `caldav` library is synchronous | Run in Celery worker (sync context), not in FastAPI async loop |
| Clock drift between iCloud and local server | Both timestamps converted to UTC before comparison |
| Celery worker can't find DB | Worker shares `DATABASE_URL` env var; uses `AsyncSessionLocal` with `run_async` bridge |
| Large initial sync (hundreds of events) | Runs as Celery task with SYNCING status; UI shows progress |
| Shared calendar duplicate events | Detection during calendar selection via UID sampling + warning |
| Fernet key rotation | Not supported in v1; document that changing key invalidates all stored passwords |
