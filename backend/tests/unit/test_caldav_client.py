"""Unit tests for CalDAV client ICS ↔ CalendarEvent mapping.

Tests ics_to_event_data and event_data_to_ics without connecting to any CalDAV server.
Also tests fallback logic when event_by_uid fails (iCloud 412 workaround).
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, call

import caldav
import caldav.lib.error
import icalendar

from app.services.caldav_client import (
    ics_to_event_data,
    event_data_to_ics,
    update_remote_event,
    delete_remote_event,
    _extract_tzid,
)


# =============================================================================
# _extract_tzid tests
# =============================================================================


class TestExtractTzid:
    """Tests for _extract_tzid helper."""

    def test_zoneinfo(self):
        """Should extract .key from ZoneInfo objects."""
        from zoneinfo import ZoneInfo

        dt = datetime(2026, 1, 15, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        assert _extract_tzid(dt) == "America/New_York"

    def test_utc_timezone(self):
        """Should return 'UTC' for stdlib timezone.utc."""
        dt = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
        assert _extract_tzid(dt) == "UTC"

    def test_naive_datetime(self):
        """Should return 'UTC' for naive datetimes."""
        dt = datetime(2026, 1, 15, 10, 0)
        assert _extract_tzid(dt) == "UTC"

    def test_pytz_zone(self):
        """Should extract .zone from pytz-like objects."""
        from datetime import tzinfo as _tzinfo

        class FakePytzZone(_tzinfo):
            """Simulate a pytz-like tzinfo with .zone but no .key."""
            zone = "Europe/London"
            def utcoffset(self, dt): return None
            def tzname(self, dt): return "GMT"
            def dst(self, dt): return None

        dt = datetime(2026, 1, 15, 10, 0, tzinfo=FakePytzZone())
        assert _extract_tzid(dt) == "Europe/London"


# =============================================================================
# ics_to_event_data tests
# =============================================================================


class TestIcsToEventData:
    """Tests for converting VEVENT → dict."""

    def _make_vevent(self, **kwargs):
        """Helper: build a VEVENT component with given properties."""
        vevent = icalendar.Event()
        for key, val in kwargs.items():
            vevent.add(key, val)
        return vevent

    def test_timed_event_utc(self):
        """Timed event with UTC times should parse correctly and extract UTC timezone."""
        vevent = self._make_vevent(
            uid="test-123",
            summary="Team Meeting",
            description="Weekly standup",
            dtstart=datetime(2026, 3, 15, 14, 0, tzinfo=timezone.utc),
            dtend=datetime(2026, 3, 15, 15, 30, tzinfo=timezone.utc),
        )
        result = ics_to_event_data(vevent)

        assert result["external_id"] == "test-123"
        assert result["title"] == "Team Meeting"
        assert result["description"] == "Weekly standup"
        assert result["date"] == date(2026, 3, 15)
        assert result["start_time"] == "14:00"
        assert result["end_time"] == "15:30"
        assert result["all_day"] is False
        assert result["timezone"] == "UTC"

    def test_timed_event_preserves_source_timezone(self):
        """Event in US/Eastern should keep times in Eastern (no conversion)."""
        from zoneinfo import ZoneInfo

        eastern = ZoneInfo("US/Eastern")
        # 10:00 AM Eastern — should be stored as-is, not converted
        vevent = self._make_vevent(
            uid="tz-test",
            summary="Eastern Meeting",
            dtstart=datetime(2026, 1, 15, 10, 0, tzinfo=eastern),
            dtend=datetime(2026, 1, 15, 11, 0, tzinfo=eastern),
        )
        result = ics_to_event_data(vevent)

        assert result["start_time"] == "10:00"
        assert result["end_time"] == "11:00"
        assert result["date"] == date(2026, 1, 15)
        assert result["timezone"] == "US/Eastern"

    def test_all_day_event(self):
        """All-day event (DTSTART is a date, not datetime)."""
        vevent = self._make_vevent(
            uid="allday-1",
            summary="Holiday",
            dtstart=date(2026, 12, 25),
            dtend=date(2026, 12, 26),
        )
        result = ics_to_event_data(vevent)

        assert result["all_day"] is True
        assert result["date"] == date(2026, 12, 25)
        assert result["start_time"] is None
        assert result["end_time"] is None
        assert result["timezone"] is None

    def test_missing_uid_returns_none(self):
        """VEVENT without UID should be skipped."""
        vevent = self._make_vevent(
            summary="No UID",
            dtstart=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        assert ics_to_event_data(vevent) is None

    def test_missing_dtstart_returns_none(self):
        """VEVENT without DTSTART should be skipped."""
        vevent = self._make_vevent(uid="no-dtstart", summary="Missing Start")
        assert ics_to_event_data(vevent) is None

    def test_last_modified_parsed(self):
        """LAST-MODIFIED should be parsed as naive UTC datetime."""
        vevent = self._make_vevent(
            uid="mod-test",
            summary="Modified Event",
            dtstart=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        )
        vevent.add("last-modified", datetime(2026, 2, 28, 18, 30, tzinfo=timezone.utc))
        result = ics_to_event_data(vevent)

        assert result["last_modified_remote"] is not None
        assert result["last_modified_remote"].year == 2026
        assert result["last_modified_remote"].month == 2
        assert result["last_modified_remote"].tzinfo is None  # Stored as naive UTC

    def test_long_title_truncated(self):
        """Titles longer than 200 chars should be truncated."""
        vevent = self._make_vevent(
            uid="long-title",
            summary="X" * 300,
            dtstart=date(2026, 1, 1),
        )
        result = ics_to_event_data(vevent)
        assert len(result["title"]) == 200

    def test_no_description_returns_none(self):
        """Missing description should return None."""
        vevent = self._make_vevent(
            uid="no-desc",
            summary="No Desc",
            dtstart=date(2026, 1, 1),
        )
        result = ics_to_event_data(vevent)
        assert result["description"] is None


# =============================================================================
# event_data_to_ics tests
# =============================================================================


class TestEventDataToIcs:
    """Tests for converting dict → iCalendar."""

    def test_timed_event(self):
        """Timed event should produce correct DTSTART/DTEND."""
        data = {
            "title": "Lunch",
            "description": "With team",
            "date": date(2026, 3, 15),
            "start_time": "12:00",
            "end_time": "13:00",
            "all_day": False,
            "external_id": "existing-uid",
        }
        cal = event_data_to_ics(data)
        ical_str = cal.to_ical().decode()

        assert "SUMMARY:Lunch" in ical_str
        assert "DESCRIPTION:With team" in ical_str
        assert "UID:existing-uid" in ical_str

        # Parse back and check
        parsed = icalendar.Calendar.from_ical(cal.to_ical())
        for comp in parsed.walk():
            if comp.name == "VEVENT":
                dtstart = comp.get("DTSTART").dt
                assert isinstance(dtstart, datetime)
                assert dtstart.hour == 12
                assert dtstart.minute == 0

    def test_all_day_event(self):
        """All-day event should have date-only DTSTART and DTEND = next day."""
        data = {
            "title": "Holiday",
            "date": date(2026, 12, 25),
            "all_day": True,
        }
        cal = event_data_to_ics(data)
        parsed = icalendar.Calendar.from_ical(cal.to_ical())

        for comp in parsed.walk():
            if comp.name == "VEVENT":
                dtstart = comp.get("DTSTART").dt
                dtend = comp.get("DTEND").dt
                assert dtstart == date(2026, 12, 25)
                assert dtend == date(2026, 12, 26)  # Exclusive end

    def test_generates_uid_when_missing(self):
        """Should generate a @familyhub.app UID when external_id is absent."""
        data = {
            "title": "New Event",
            "date": date(2026, 1, 1),
            "all_day": True,
        }
        cal = event_data_to_ics(data)
        ical_str = cal.to_ical().decode()
        assert "@familyhub.app" in ical_str


# =============================================================================
# Round-trip test
# =============================================================================


class TestRoundTrip:
    """Test that event_data_to_ics → ics_to_event_data preserves data."""

    def test_timed_event_round_trip(self):
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/New_York")
        original = {
            "title": "Round Trip",
            "description": "Test desc",
            "date": date(2026, 6, 15),
            "start_time": "09:30",
            "end_time": "10:45",
            "all_day": False,
            "external_id": "rt-uid-1",
        }
        cal = event_data_to_ics(original, tz=tz)

        # Parse back
        parsed = icalendar.Calendar.from_ical(cal.to_ical())
        for comp in parsed.walk():
            if comp.name == "VEVENT":
                result = ics_to_event_data(comp)
                assert result["title"] == "Round Trip"
                assert result["description"] == "Test desc"
                assert result["date"] == date(2026, 6, 15)
                assert result["start_time"] == "09:30"
                assert result["end_time"] == "10:45"
                assert result["all_day"] is False
                assert result["external_id"] == "rt-uid-1"
                assert result["timezone"] == "America/New_York"

    def test_all_day_round_trip(self):
        original = {
            "title": "All Day RT",
            "date": date(2026, 7, 4),
            "all_day": True,
            "external_id": "rt-uid-2",
        }
        cal = event_data_to_ics(original)

        parsed = icalendar.Calendar.from_ical(cal.to_ical())
        for comp in parsed.walk():
            if comp.name == "VEVENT":
                result = ics_to_event_data(comp)
                assert result["title"] == "All Day RT"
                assert result["date"] == date(2026, 7, 4)
                assert result["all_day"] is True
                assert result["start_time"] is None
                assert result["end_time"] is None
                assert result["timezone"] is None


# =============================================================================
# update_remote_event / delete_remote_event fallback tests
# =============================================================================


def _make_mock_calendar(url="https://caldav.icloud.com/cal/test-cal/"):
    """Build a mock caldav.Calendar with event_by_uid that raises ReportError."""
    mock_cal = MagicMock(spec=caldav.Calendar)
    mock_cal.url = url
    mock_cal.event_by_uid.side_effect = caldav.lib.error.ReportError(
        "412 Precondition Failed"
    )
    return mock_cal


class TestUpdateRemoteEventModifiesICS:
    """Tests that update_remote_event correctly modifies ICS data via icalendar_instance."""

    def test_updates_summary_and_saves(self):
        """Should modify VEVENT SUMMARY via icalendar_instance property and save."""
        # Build a real icalendar object
        cal = icalendar.Calendar()
        vevent = icalendar.Event()
        vevent.add("uid", "test-uid")
        vevent.add("summary", "Original Title")
        vevent.add("dtstart", datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc))
        vevent.add("dtend", datetime(2026, 3, 15, 11, 0, tzinfo=timezone.utc))
        cal.add_component(vevent)

        mock_event = MagicMock()
        mock_event.icalendar_instance = cal

        mock_cal = MagicMock(spec=caldav.Calendar)
        mock_cal.event_by_uid.return_value = mock_event

        update_remote_event(
            mock_cal, "test-uid",
            {"title": "Updated Title", "date": date(2026, 3, 15), "start_time": "10:00", "all_day": False},
        )

        # Verify the VEVENT was modified
        for comp in cal.subcomponents:
            if comp.name == "VEVENT":
                assert str(comp["SUMMARY"]) == "Updated Title"

        # Verify icalendar_instance was written back and save called
        assert mock_event.icalendar_instance == cal
        mock_event.save.assert_called_once()

    def test_does_not_use_edit_icalendar_instance(self):
        """Should NOT call edit_icalendar_instance (doesn't exist in caldav 2.2.6)."""
        cal = icalendar.Calendar()
        vevent = icalendar.Event()
        vevent.add("uid", "test-uid-2")
        vevent.add("summary", "Test")
        vevent.add("dtstart", date(2026, 1, 1))
        cal.add_component(vevent)

        mock_event = MagicMock()
        mock_event.icalendar_instance = cal

        mock_cal = MagicMock(spec=caldav.Calendar)
        mock_cal.event_by_uid.return_value = mock_event

        update_remote_event(mock_cal, "test-uid-2", {"title": "New", "date": date(2026, 1, 1), "all_day": True})

        # edit_icalendar_instance should never be called
        mock_event.edit_icalendar_instance.assert_not_called()


class TestUpdateRemoteEventFallback:
    """Tests for iCloud 412 fallback in update_remote_event."""

    def test_falls_back_to_direct_url_on_report_error(self):
        """When event_by_uid raises ReportError, should use direct URL access."""
        mock_cal = _make_mock_calendar()
        uid = "71E273EE-C0F3-48FB-A953-26D2C82388D7"
        event_data = {"title": "Updated Golf", "date": date(2026, 2, 26)}

        mock_event = MagicMock()
        with patch("app.services.caldav_client.caldav.Event", return_value=mock_event) as mock_cls:
            update_remote_event(mock_cal, uid, event_data)

            # Verify event_by_uid was attempted first
            mock_cal.event_by_uid.assert_called_once_with(uid)

            # Verify fallback constructed direct URL
            expected_url = f"https://caldav.icloud.com/cal/test-cal/{uid}.ics"
            mock_cls.assert_called_once_with(
                client=mock_cal.client, url=expected_url, parent=mock_cal
            )
            mock_event.load.assert_called_once()
            mock_event.save.assert_called_once()

    def test_uses_event_by_uid_when_available(self):
        """When event_by_uid succeeds, should use it normally (no fallback)."""
        mock_cal = MagicMock(spec=caldav.Calendar)
        mock_event = MagicMock()
        mock_cal.event_by_uid.return_value = mock_event
        uid = "normal-uid"
        event_data = {"title": "Normal Update", "date": date(2026, 3, 1)}

        with patch("app.services.caldav_client.caldav.Event") as mock_cls:
            update_remote_event(mock_cal, uid, event_data)
            mock_cls.assert_not_called()  # No fallback needed

        mock_cal.event_by_uid.assert_called_once_with(uid)
        mock_event.save.assert_called_once()


class TestPushPreservesLocalTimezone:
    """Regression tests: pushed events must use TZID notation, not UTC Z-suffix.

    Bug: _apply_times_to_vevent converted local times to UTC before adding to
    VEVENT, producing DTSTART:20260310T190000Z. iCloud's Edit Event modal then
    showed the raw UTC time (7:00 PM) instead of the local time (12:00 PM).
    Fix: keep times in the user's local timezone so icalendar produces
    DTSTART;TZID=America/...:20260310T120000.
    """

    def test_event_data_to_ics_preserves_timezone(self):
        """event_data_to_ics with tz should produce TZID, not UTC Z-suffix."""
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/New_York")
        data = {
            "title": "Test Time Sync",
            "date": date(2026, 3, 10),
            "start_time": "12:00",
            "end_time": "15:00",
            "all_day": False,
            "external_id": "tz-push-test",
        }
        cal = event_data_to_ics(data, tz=tz)
        ical_str = cal.to_ical().decode()

        # Must NOT contain UTC Z-suffix for timed event
        # (Z-suffix means iCloud shows raw UTC in Edit Event modal)
        assert "T120000Z" not in ical_str, (
            "DTSTART should not be in UTC Z notation — iCloud Edit Event modal "
            "shows raw UTC times when Z-suffix is used"
        )

        # Must contain TZID reference to preserve local time display
        assert "TZID" in ical_str, (
            "DTSTART should include TZID so iCloud Edit Event modal "
            "shows the correct local time"
        )

        # Parse back and verify the local time is preserved (not shifted)
        parsed = icalendar.Calendar.from_ical(cal.to_ical())
        for comp in parsed.walk():
            if comp.name == "VEVENT":
                dtstart = comp.get("DTSTART").dt
                assert dtstart.hour == 12, f"Expected 12:00 local, got {dtstart.hour}:00"
                assert dtstart.minute == 0
                dtend = comp.get("DTEND").dt
                assert dtend.hour == 15, f"Expected 15:00 local, got {dtend.hour}:00"

    def test_update_remote_event_preserves_timezone(self):
        """update_remote_event with tz should write TZID times, not UTC."""
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Los_Angeles")

        # Build a VEVENT that simulates what iCloud returns (with TZID)
        cal = icalendar.Calendar()
        vevent = icalendar.Event()
        vevent.add("uid", "push-tz-uid")
        vevent.add("summary", "Original")
        vevent.add("dtstart", datetime(2026, 3, 10, 12, 0, tzinfo=tz))
        vevent.add("dtend", datetime(2026, 3, 10, 13, 0, tzinfo=tz))
        cal.add_component(vevent)

        mock_event = MagicMock()
        mock_event.icalendar_instance = cal

        mock_cal = MagicMock(spec=caldav.Calendar)
        mock_cal.event_by_uid.return_value = mock_event

        update_remote_event(
            mock_cal, "push-tz-uid",
            {
                "title": "Updated",
                "date": date(2026, 3, 10),
                "start_time": "12:00",
                "end_time": "15:00",
                "all_day": False,
            },
            tz=tz,
        )

        # Check the ICS output has TZID, not UTC Z-suffix
        ical_str = cal.to_ical().decode()
        assert "T120000Z" not in ical_str, (
            "Updated DTSTART should not use UTC Z notation"
        )
        assert "TZID" in ical_str, (
            "Updated DTSTART should include TZID for correct iCloud display"
        )

    def test_round_trip_with_timezone_preserves_local_times(self):
        """Pull then push should preserve times correctly with per-event timezone."""
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/New_York")

        # Simulate pull: iCloud has event at 12:00 EST (stored in VEVENT as 12:00 with TZID)
        vevent_pull = icalendar.Event()
        vevent_pull.add("uid", "rt-tz-uid")
        vevent_pull.add("summary", "Round Trip TZ")
        vevent_pull.add("dtstart", datetime(2026, 1, 15, 12, 0, tzinfo=tz))
        vevent_pull.add("dtend", datetime(2026, 1, 15, 15, 0, tzinfo=tz))

        pulled = ics_to_event_data(vevent_pull)
        assert pulled["start_time"] == "12:00"  # Preserved as-is in event's tz
        assert pulled["end_time"] == "15:00"
        assert pulled["timezone"] == "America/New_York"

        # Simulate push: send pulled data back to iCloud using event's timezone
        push_data = {
            "title": pulled["title"],
            "date": pulled["date"],
            "start_time": pulled["start_time"],
            "end_time": pulled["end_time"],
            "all_day": False,
            "external_id": pulled["external_id"],
        }
        cal = event_data_to_ics(push_data, tz=tz)

        # Parse the pushed ICS and verify times match original
        parsed = icalendar.Calendar.from_ical(cal.to_ical())
        for comp in parsed.walk():
            if comp.name == "VEVENT":
                dtstart = comp.get("DTSTART").dt
                assert dtstart.hour == 12, (
                    f"Round-trip should preserve 12:00 local, got {dtstart.hour}:00"
                )
                # Convert to UTC to verify semantic correctness
                dtstart_utc = dtstart.astimezone(timezone.utc)
                assert dtstart_utc.hour == 17, (
                    f"12:00 EST should be 17:00 UTC, got {dtstart_utc.hour}:00"
                )


class TestDeleteRemoteEventFallback:
    """Tests for iCloud 412 fallback in delete_remote_event."""

    def test_falls_back_to_direct_url_on_report_error(self):
        """When event_by_uid raises ReportError, should delete via direct URL."""
        mock_cal = _make_mock_calendar()
        uid = "delete-test-uid"

        mock_event = MagicMock()
        with patch("app.services.caldav_client.caldav.Event", return_value=mock_event) as mock_cls:
            delete_remote_event(mock_cal, uid)

            expected_url = f"https://caldav.icloud.com/cal/test-cal/{uid}.ics"
            mock_cls.assert_called_once_with(
                client=mock_cal.client, url=expected_url, parent=mock_cal
            )
            mock_event.delete.assert_called_once()

    def test_uses_event_by_uid_when_available(self):
        """When event_by_uid succeeds, should delete normally."""
        mock_cal = MagicMock(spec=caldav.Calendar)
        mock_event = MagicMock()
        mock_cal.event_by_uid.return_value = mock_event

        with patch("app.services.caldav_client.caldav.Event") as mock_cls:
            delete_remote_event(mock_cal, "normal-uid")
            mock_cls.assert_not_called()

        mock_event.delete.assert_called_once()
