"""CalDAV client wrapper for iCloud Calendar operations.

This module wraps the `caldav` library with iCloud-specific defaults and
provides ICS ↔ CalendarEvent field mapping. All functions are synchronous —
they run inside Celery workers, not the async FastAPI event loop.
"""

import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import caldav
import icalendar

logger = logging.getLogger(__name__)

ICLOUD_CALDAV_URL = "https://caldav.icloud.com/"


def _extract_tzid(dt: datetime) -> str:
    """Extract IANA timezone name from a datetime's tzinfo.

    Tries .key (ZoneInfo), .zone (pytz), then falls back to "UTC".
    Returns "UTC" for naive datetimes or unrecognised tzinfo.
    """
    if dt.tzinfo is None:
        return "UTC"
    # ZoneInfo objects have a .key attribute
    key = getattr(dt.tzinfo, "key", None)
    if key:
        return key
    # pytz zones have a .zone attribute
    zone = getattr(dt.tzinfo, "zone", None)
    if zone:
        return zone
    # stdlib timezone.utc
    if dt.tzinfo == timezone.utc:
        return "UTC"
    return "UTC"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def connect_icloud(email: str, password: str):
    """Connect to iCloud CalDAV and return (client, principal).

    Raises caldav.lib.error.AuthorizationError on bad credentials.
    """
    client = caldav.DAVClient(
        url=ICLOUD_CALDAV_URL,
        username=email,
        password=password,
    )
    principal = client.principal()  # validates credentials
    return client, principal


# ---------------------------------------------------------------------------
# Calendar listing
# ---------------------------------------------------------------------------


def list_calendars(principal) -> list[dict]:
    """List available calendars from an iCloud account.

    Returns: [{"url": str, "name": str, "color": str | None}]
    """
    calendars = principal.calendars()
    result = []
    for cal in calendars:
        name = cal.name or str(cal.url)
        # Try to get calendar color from properties
        color = None
        try:
            props = cal.get_properties(
                [caldav.dav.DisplayName(), caldav.elements.ical.CalendarColor()]
            )
            for key, val in props.items():
                if "calendar-color" in str(key).lower():
                    color = str(val)
        except Exception:
            pass  # Color is optional, don't fail on it

        result.append(
            {
                "url": str(cal.url),
                "name": name,
                "color": color,
            }
        )
    return result


# ---------------------------------------------------------------------------
# Fetch events
# ---------------------------------------------------------------------------


def fetch_events(
    calendar: caldav.Calendar,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Fetch events from a calendar within a date range.

    Filters out recurring events (RRULE present) for v1.
    Returns a list of dicts from ics_to_event_data().
    """
    start_dt = datetime.combine(start_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(
        tzinfo=timezone.utc
    )

    try:
        raw_events = calendar.search(
            start=start_dt,
            end=end_dt,
            event=True,
            expand=True,
        )
    except Exception:
        # Fallback to date_search for older CalDAV servers
        raw_events = calendar.date_search(
            start=start_dt,
            end=end_dt,
            expand=True,
        )

    results = []
    for event_obj in raw_events:
        try:
            cal_data = icalendar.Calendar.from_ical(event_obj.data)
            for component in cal_data.walk():
                if component.name != "VEVENT":
                    continue

                # Skip recurring events in v1
                if component.get("RRULE"):
                    uid = str(component.get("UID", "unknown"))
                    logger.debug(
                        "Skipping recurring event UID=%s (v1: single events only)",
                        uid,
                    )
                    continue

                parsed = ics_to_event_data(component)
                if parsed:
                    # Attach the etag from the CalDAV object for change detection
                    parsed["etag"] = getattr(event_obj, "etag", None)
                    results.append(parsed)
        except Exception:
            logger.warning(
                "Failed to parse event from CalDAV, skipping",
                exc_info=True,
            )

    return results


# ---------------------------------------------------------------------------
# Remote CRUD
# ---------------------------------------------------------------------------


def create_remote_event(
    calendar: caldav.Calendar, event_data: dict, tz: ZoneInfo | None = None
) -> str:
    """Create an event on iCloud. Returns the UID."""
    cal = event_data_to_ics(event_data, tz=tz)
    created = calendar.save_event(cal.to_ical().decode("utf-8"))
    # Extract UID from the saved event
    parsed = icalendar.Calendar.from_ical(created.data)
    for comp in parsed.walk():
        if comp.name == "VEVENT":
            return str(comp.get("UID"))
    return None


def _get_event_by_uid(calendar: caldav.Calendar, uid: str):
    """Look up a CalDAV event by UID with fallback for iCloud 412 errors.

    iCloud sometimes returns 412 Precondition Failed on REPORT queries
    used by event_by_uid(). When that happens, fall back to direct URL
    access at {calendar_url}/{uid}.ics (standard CalDAV convention).
    """
    try:
        return calendar.event_by_uid(uid)
    except Exception as e:
        base = str(calendar.url).rstrip("/")
        url = f"{base}/{uid}.ics"
        logger.warning(
            "event_by_uid failed for UID=%s (%s), trying direct URL: %s",
            uid,
            e,
            url,
        )
        event_obj = caldav.Event(client=calendar.client, url=url, parent=calendar)
        event_obj.load()
        return event_obj


def update_remote_event(
    calendar: caldav.Calendar, uid: str, event_data: dict, tz: ZoneInfo | None = None
) -> None:
    """Update an existing event on iCloud by UID."""
    event_obj = _get_event_by_uid(calendar, uid)
    cal = event_obj.icalendar_instance
    for comp in cal.subcomponents:
        if comp.name == "VEVENT":
            if "title" in event_data:
                comp["SUMMARY"] = event_data["title"]
            if "description" in event_data:
                if event_data["description"]:
                    comp["DESCRIPTION"] = event_data["description"]
                elif "DESCRIPTION" in comp:
                    del comp["DESCRIPTION"]
            _apply_times_to_vevent(comp, event_data, tz=tz)
    event_obj.icalendar_instance = cal
    event_obj.save()


def delete_remote_event(calendar: caldav.Calendar, uid: str) -> None:
    """Delete an event from iCloud by UID."""
    event_obj = _get_event_by_uid(calendar, uid)
    event_obj.delete()


def move_event(
    principal,
    source_cal_url: str,
    dest_cal_url: str,
    uid: str,
) -> None:
    """Move an event from one calendar to another on the same iCloud account.

    Tries HTTP MOVE first; falls back to delete+create if MOVE fails.
    """
    source_cal = get_calendar_by_url(principal, source_cal_url)
    dest_cal = get_calendar_by_url(principal, dest_cal_url)

    event_obj = _get_event_by_uid(source_cal, uid)
    ical_data = event_obj.data

    try:
        # Try to save the event data to the destination calendar
        dest_cal.save_event(ical_data)
        # Delete from source
        event_obj.delete()
        logger.info("Moved event UID=%s via save+delete", uid)
    except Exception as e:
        logger.error("Failed to move event UID=%s: %s", uid, e, exc_info=True)
        raise


def get_calendar_by_url(principal, calendar_url: str) -> caldav.Calendar:
    """Get a specific calendar object by its URL."""
    return principal.calendar(cal_id=calendar_url)


# ---------------------------------------------------------------------------
# ICS ↔ CalendarEvent mapping
# ---------------------------------------------------------------------------


def ics_to_event_data(vevent) -> dict | None:
    """Convert an iCalendar VEVENT component to a dict matching CalendarEventCreate fields.

    Times are stored as-is in the VEVENT's own timezone. The timezone name is
    extracted and included in the returned dict so it can be stored per-event.

    Mapping:
    - SUMMARY → title
    - DESCRIPTION → description
    - DTSTART → date + start_time (in event's own timezone)
    - DTEND → end_time
    - UID → external_id
    - LAST-MODIFIED → last_modified_remote (always UTC)
    - All-day: DTSTART is a date (not datetime)
    - timezone: IANA name extracted from DTSTART's tzinfo
    """
    uid = vevent.get("UID")
    if not uid:
        logger.warning("VEVENT missing UID, skipping")
        return None

    summary = str(vevent.get("SUMMARY", "Untitled"))
    description = str(vevent.get("DESCRIPTION", "")) or None

    # Parse DTSTART
    dtstart_prop = vevent.get("DTSTART")
    if not dtstart_prop:
        logger.warning("VEVENT UID=%s missing DTSTART, skipping", uid)
        return None

    dtstart = dtstart_prop.dt

    # Detect all-day event: DTSTART is a date, not datetime
    is_all_day = isinstance(dtstart, date) and not isinstance(dtstart, datetime)

    if is_all_day:
        event_date = dtstart
        start_time = None
        end_time = None
        event_tz = None
    else:
        # Extract timezone from the VEVENT's own DTSTART
        event_tz = _extract_tzid(dtstart)

        # Use the time as-is in its own timezone (no conversion)
        event_date = dtstart.date()
        start_time = dtstart.strftime("%H:%M")

        # Parse DTEND
        dtend_prop = vevent.get("DTEND")
        if dtend_prop:
            dtend = dtend_prop.dt
            end_time = dtend.strftime("%H:%M")
        else:
            end_time = None

    # Parse LAST-MODIFIED (always UTC — this is sync metadata, not display time)
    last_modified = None
    last_mod_prop = vevent.get("LAST-MODIFIED")
    if last_mod_prop:
        lm = last_mod_prop.dt
        if isinstance(lm, datetime):
            if lm.tzinfo is not None:
                lm = lm.astimezone(timezone.utc)
            last_modified = lm.replace(tzinfo=None)  # Store as naive UTC

    return {
        "external_id": str(uid),
        "title": summary[:200],  # Respect max_length
        "description": description[:500] if description else None,
        "date": event_date,
        "start_time": start_time,
        "end_time": end_time,
        "all_day": is_all_day,
        "timezone": event_tz,
        "last_modified_remote": last_modified,
    }


def event_data_to_ics(event_data: dict, tz: ZoneInfo | None = None) -> icalendar.Calendar:
    """Convert CalendarEvent fields to an iCalendar object for pushing to iCloud.

    Args:
        tz: If provided, HH:MM times in event_data are interpreted as local time
            in this timezone and kept with TZID in the ICS (not converted to UTC).
    """
    cal = icalendar.Calendar()
    cal.add("prodid", "-//Family Hub//familyhub.app//")
    cal.add("version", "2.0")

    vevent = icalendar.Event()
    vevent.add("summary", event_data.get("title", "Untitled"))

    if event_data.get("description"):
        vevent.add("description", event_data["description"])

    _apply_times_to_vevent(vevent, event_data, tz=tz)

    # UID — use existing external_id if available, otherwise generate
    if event_data.get("external_id"):
        vevent.add("uid", event_data["external_id"])
    else:
        import uuid

        vevent.add("uid", f"{uuid.uuid4()}@familyhub.app")

    vevent.add("dtstamp", datetime.now(timezone.utc))

    cal.add_component(vevent)
    return cal


def _apply_times_to_vevent(
    vevent, event_data: dict, tz: ZoneInfo | None = None
) -> None:
    """Set DTSTART/DTEND on a VEVENT from event_data fields.

    Args:
        tz: If provided, HH:MM times are interpreted as local time in this
            timezone and kept with TZID in the ICS output (not converted to UTC).
            This ensures iCloud's Edit Event modal shows the correct local time.

    Handles both all-day and timed events.
    """
    event_date = event_data.get("date")
    if not event_date:
        return

    if isinstance(event_date, str):
        event_date = date.fromisoformat(event_date)

    is_all_day = event_data.get("all_day", False)

    # Remove existing time properties before setting new ones
    for prop in ("DTSTART", "DTEND"):
        if prop in vevent:
            del vevent[prop]

    if is_all_day:
        vevent.add("dtstart", event_date)
        # All-day events: DTEND is next day (exclusive end)
        from datetime import timedelta

        vevent.add("dtend", event_date + timedelta(days=1))
    else:
        # Interpret HH:MM as local time in `tz`, then convert to UTC
        source_tz = tz or timezone.utc
        start_time = event_data.get("start_time", "00:00")
        h, m = map(int, start_time.split(":"))
        dtstart_local = datetime(
            event_date.year, event_date.month, event_date.day, h, m,
            tzinfo=source_tz,
        )
        vevent.add("dtstart", dtstart_local)

        end_time = event_data.get("end_time")
        if end_time:
            eh, em = map(int, end_time.split(":"))
            dtend_local = datetime(
                event_date.year, event_date.month, event_date.day, eh, em,
                tzinfo=source_tz,
            )
            vevent.add("dtend", dtend_local)


# ---------------------------------------------------------------------------
# VTODO (Reminders) operations
# ---------------------------------------------------------------------------


def list_reminder_lists(principal) -> list[dict]:
    """List available reminder/todo lists from an iCloud account.

    Filters calendars by VTODO component support.
    Returns: [{"url": str, "name": str, "color": str | None}]
    """
    calendars = principal.calendars()
    result = []
    for cal in calendars:
        # Check if calendar supports VTODOs
        try:
            supported = cal.get_supported_components()
            if supported and "VTODO" not in supported:
                continue
        except Exception:
            # If we can't determine supported components, try fetching todos
            try:
                cal.todos(include_completed=False)
            except Exception:
                continue

        name = cal.name or str(cal.url)
        color = None
        try:
            props = cal.get_properties(
                [caldav.dav.DisplayName(), caldav.elements.ical.CalendarColor()]
            )
            for key, val in props.items():
                if "calendar-color" in str(key).lower():
                    color = str(val)
        except Exception:
            pass

        result.append({"url": str(cal.url), "name": name, "color": color})
    return result


def fetch_todos(calendar: caldav.Calendar) -> list[dict]:
    """Fetch incomplete + recently completed VTODOs from a calendar.

    No date windowing — fetches all incomplete todos and completed within last 30 days.
    Returns a list of dicts from vtodo_to_task_data().
    """
    results = []

    # Fetch incomplete todos
    try:
        incomplete = calendar.todos(include_completed=False)
    except Exception:
        logger.warning("Failed to fetch incomplete todos", exc_info=True)
        incomplete = []

    # Fetch completed todos (recent)
    try:
        completed = calendar.todos(include_completed=True)
        # Filter to only completed ones (not already in incomplete)
        incomplete_uids = set()
        for t in incomplete:
            try:
                cal_data = icalendar.Calendar.from_ical(t.data)
                for comp in cal_data.walk():
                    if comp.name == "VTODO" and comp.get("UID"):
                        incomplete_uids.add(str(comp.get("UID")))
            except Exception:
                pass
        completed = [t for t in completed if _get_todo_uid(t) not in incomplete_uids]
    except Exception:
        logger.warning("Failed to fetch completed todos", exc_info=True)
        completed = []

    for todo_obj in incomplete + completed:
        try:
            cal_data = icalendar.Calendar.from_ical(todo_obj.data)
            for component in cal_data.walk():
                if component.name != "VTODO":
                    continue
                parsed = vtodo_to_task_data(component)
                if parsed:
                    parsed["etag"] = getattr(todo_obj, "etag", None)
                    results.append(parsed)
        except Exception:
            logger.warning("Failed to parse VTODO, skipping", exc_info=True)

    return results


def _get_todo_uid(todo_obj) -> str | None:
    """Extract UID from a CalDAV todo object."""
    try:
        cal_data = icalendar.Calendar.from_ical(todo_obj.data)
        for comp in cal_data.walk():
            if comp.name == "VTODO" and comp.get("UID"):
                return str(comp.get("UID"))
    except Exception:
        pass
    return None


def vtodo_to_task_data(vtodo) -> dict | None:
    """Convert an iCalendar VTODO component to a dict matching Task fields.

    Mapping:
    - SUMMARY → title
    - DESCRIPTION → description
    - DUE → due_date (nullable — reminders don't require a due date)
    - PRIORITY → priority (0=none, 1=high, 5=medium, 9=low)
    - STATUS → completed (COMPLETED = True)
    - COMPLETED → completed_at
    - RELATED-TO → parent_external_id
    - UID → external_id
    - LAST-MODIFIED → last_modified_remote
    """
    uid = vtodo.get("UID")
    if not uid:
        logger.warning("VTODO missing UID, skipping")
        return None

    summary = vtodo.get("SUMMARY")
    if not summary:
        logger.warning("VTODO UID=%s missing SUMMARY, skipping", uid)
        return None

    title = str(summary)[:100]  # Respect max_length
    description = str(vtodo.get("DESCRIPTION", "")) or None
    if description:
        description = description[:500]

    # Parse DUE (optional for reminders)
    due_date = None
    due_prop = vtodo.get("DUE")
    if due_prop:
        dt = due_prop.dt
        if isinstance(dt, datetime):
            due_date = dt
        elif isinstance(dt, date):
            due_date = datetime.combine(dt, datetime.min.time())

    # Parse PRIORITY (iCalendar standard: 0=undefined, 1-4=high, 5=medium, 6-9=low)
    priority = 0
    prio_prop = vtodo.get("PRIORITY")
    if prio_prop:
        prio_val = int(prio_prop)
        if 1 <= prio_val <= 4:
            priority = 1  # High
        elif prio_val == 5:
            priority = 5  # Medium
        elif 6 <= prio_val <= 9:
            priority = 9  # Low
        # 0 = none/undefined → 0

    # Parse STATUS
    status = str(vtodo.get("STATUS", "")).upper()
    completed = status == "COMPLETED"

    # Parse COMPLETED timestamp
    completed_at = None
    completed_prop = vtodo.get("COMPLETED")
    if completed_prop:
        cat = completed_prop.dt
        if isinstance(cat, datetime):
            if cat.tzinfo:
                cat = cat.astimezone(timezone.utc)
            completed_at = cat.replace(tzinfo=None)

    # Parse RELATED-TO for subtask parent
    parent_external_id = None
    related = vtodo.get("RELATED-TO")
    if related:
        parent_external_id = str(related)

    # Parse LAST-MODIFIED
    last_modified = None
    last_mod_prop = vtodo.get("LAST-MODIFIED")
    if last_mod_prop:
        lm = last_mod_prop.dt
        if isinstance(lm, datetime):
            if lm.tzinfo:
                lm = lm.astimezone(timezone.utc)
            last_modified = lm.replace(tzinfo=None)

    return {
        "external_id": str(uid),
        "title": title,
        "description": description,
        "due_date": due_date,
        "priority": priority,
        "completed": completed,
        "completed_at": completed_at,
        "parent_external_id": parent_external_id,
        "last_modified_remote": last_modified,
    }


def task_data_to_vtodo(task_data: dict) -> icalendar.Calendar:
    """Convert Task fields to an iCalendar VTODO object for pushing to iCloud."""
    cal = icalendar.Calendar()
    cal.add("prodid", "-//Family Hub//familyhub.app//")
    cal.add("version", "2.0")

    vtodo = icalendar.Todo()
    vtodo.add("summary", task_data.get("title", "Untitled"))

    if task_data.get("description"):
        vtodo.add("description", task_data["description"])

    # DUE date
    if task_data.get("due_date"):
        due = task_data["due_date"]
        if isinstance(due, str):
            due = datetime.fromisoformat(due)
        if isinstance(due, datetime):
            vtodo.add("due", due)
        elif isinstance(due, date):
            vtodo.add("due", due)

    # PRIORITY
    priority = task_data.get("priority", 0)
    vtodo.add("priority", priority)

    # STATUS + COMPLETED
    if task_data.get("completed"):
        vtodo.add("status", "COMPLETED")
        if task_data.get("completed_at"):
            cat = task_data["completed_at"]
            if isinstance(cat, str):
                cat = datetime.fromisoformat(cat)
            vtodo.add("completed", cat)
    else:
        vtodo.add("status", "NEEDS-ACTION")

    # RELATED-TO for subtask parent
    if task_data.get("parent_external_id"):
        vtodo.add("related-to", task_data["parent_external_id"])

    # UID
    if task_data.get("external_id"):
        vtodo.add("uid", task_data["external_id"])
    else:
        import uuid
        vtodo.add("uid", f"{uuid.uuid4()}@familyhub.app")

    vtodo.add("dtstamp", datetime.now(timezone.utc))

    cal.add_component(vtodo)
    return cal


def create_remote_todo(calendar: caldav.Calendar, task_data: dict) -> str:
    """Create a VTODO on iCloud. Returns the UID."""
    cal = task_data_to_vtodo(task_data)
    created = calendar.save_todo(cal.to_ical().decode("utf-8"))
    parsed = icalendar.Calendar.from_ical(created.data)
    for comp in parsed.walk():
        if comp.name == "VTODO":
            return str(comp.get("UID"))
    raise ValueError("Created VTODO but no UID in response — iCloud may have rejected it")


def _get_todo_by_uid(calendar: caldav.Calendar, uid: str):
    """Look up a CalDAV todo by UID with fallback for iCloud 412 errors."""
    try:
        return calendar.todo_by_uid(uid)
    except Exception as e:
        # Fallback to direct URL access (same pattern as _get_event_by_uid)
        base = str(calendar.url).rstrip("/")
        url = f"{base}/{uid}.ics"
        logger.warning(
            "todo_by_uid failed for UID=%s (%s), trying direct URL: %s",
            uid, e, url,
        )
        todo_obj = caldav.Todo(client=calendar.client, url=url, parent=calendar)
        todo_obj.load()
        return todo_obj


def update_remote_todo(calendar: caldav.Calendar, uid: str, task_data: dict) -> None:
    """Update an existing VTODO on iCloud by UID."""
    event_obj = _get_todo_by_uid(calendar, uid)
    cal = event_obj.icalendar_instance
    for comp in cal.subcomponents:
        if comp.name == "VTODO":
            if "title" in task_data:
                comp["SUMMARY"] = task_data["title"]
            if "description" in task_data:
                if task_data["description"]:
                    comp["DESCRIPTION"] = task_data["description"]
                elif "DESCRIPTION" in comp:
                    del comp["DESCRIPTION"]
            # Update priority
            if "priority" in task_data:
                if "PRIORITY" in comp:
                    del comp["PRIORITY"]
                comp.add("priority", task_data["priority"])
            # Update status
            if "completed" in task_data:
                if "STATUS" in comp:
                    del comp["STATUS"]
                if "COMPLETED" in comp:
                    del comp["COMPLETED"]
                if task_data["completed"]:
                    comp.add("status", "COMPLETED")
                    if task_data.get("completed_at"):
                        comp.add("completed", task_data["completed_at"])
                else:
                    comp.add("status", "NEEDS-ACTION")
            # Update due date
            if "due_date" in task_data:
                if "DUE" in comp:
                    del comp["DUE"]
                if task_data["due_date"]:
                    comp.add("due", task_data["due_date"])
    event_obj.icalendar_instance = cal
    event_obj.save()


def delete_remote_todo(calendar: caldav.Calendar, uid: str) -> None:
    """Delete a VTODO from iCloud by UID."""
    todo_obj = _get_todo_by_uid(calendar, uid)
    todo_obj.delete()
