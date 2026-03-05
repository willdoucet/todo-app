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
