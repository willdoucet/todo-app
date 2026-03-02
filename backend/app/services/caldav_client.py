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
    tz: ZoneInfo | None = None,
) -> list[dict]:
    """Fetch events from a calendar within a date range.

    Args:
        tz: If provided, timed events are converted to this timezone.

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

                parsed = ics_to_event_data(component, tz=tz)
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


def get_calendar_by_url(principal, calendar_url: str) -> caldav.Calendar:
    """Get a specific calendar object by its URL."""
    return principal.calendar(cal_id=calendar_url)


# ---------------------------------------------------------------------------
# ICS ↔ CalendarEvent mapping
# ---------------------------------------------------------------------------


def ics_to_event_data(vevent, tz: ZoneInfo | None = None) -> dict | None:
    """Convert an iCalendar VEVENT component to a dict matching CalendarEventCreate fields.

    Args:
        vevent: iCalendar VEVENT component
        tz: If provided, convert timed events to this timezone instead of UTC.
            All-day events are unaffected.

    Mapping:
    - SUMMARY → title
    - DESCRIPTION → description
    - DTSTART → date + start_time (converted to tz or UTC)
    - DTEND → end_time
    - UID → external_id
    - LAST-MODIFIED → last_modified_remote (always UTC)
    - All-day: DTSTART is a date (not datetime)
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

    target_tz = tz or timezone.utc

    if is_all_day:
        event_date = dtstart
        start_time = None
        end_time = None
    else:
        # Convert to target timezone (user's local tz, or UTC as fallback)
        if dtstart.tzinfo is not None:
            dtstart = dtstart.astimezone(target_tz)
        event_date = dtstart.date()
        start_time = dtstart.strftime("%H:%M")

        # Parse DTEND
        dtend_prop = vevent.get("DTEND")
        if dtend_prop:
            dtend = dtend_prop.dt
            if dtend.tzinfo is not None:
                dtend = dtend.astimezone(target_tz)
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
        "last_modified_remote": last_modified,
    }


def event_data_to_ics(event_data: dict, tz: ZoneInfo | None = None) -> icalendar.Calendar:
    """Convert CalendarEvent fields to an iCalendar object for pushing to iCloud.

    Args:
        tz: If provided, HH:MM times in event_data are interpreted as local time
            in this timezone and converted to UTC for the ICS.
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
            timezone and converted to UTC for the ICS output.

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
        vevent.add("dtstart", dtstart_local.astimezone(timezone.utc))

        end_time = event_data.get("end_time")
        if end_time:
            eh, em = map(int, end_time.split(":"))
            dtend_local = datetime(
                event_date.year, event_date.month, event_date.day, eh, em,
                tzinfo=source_tz,
            )
            vevent.add("dtend", dtend_local.astimezone(timezone.utc))
