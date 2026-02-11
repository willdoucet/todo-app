"""Unit tests for CalDAV client ICS ↔ CalendarEvent mapping.

Tests ics_to_event_data and event_data_to_ics without connecting to any CalDAV server.
"""

import pytest
from datetime import date, datetime, timezone, timedelta

import icalendar

from app.services.caldav_client import ics_to_event_data, event_data_to_ics


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
        """Timed event with UTC times should parse correctly."""
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

    def test_timed_event_with_timezone_conversion(self):
        """Event in US/Eastern should be converted to UTC."""
        from zoneinfo import ZoneInfo

        eastern = ZoneInfo("US/Eastern")
        # 10:00 AM Eastern = 15:00 UTC (during EST, UTC-5)
        vevent = self._make_vevent(
            uid="tz-test",
            summary="Eastern Meeting",
            dtstart=datetime(2026, 1, 15, 10, 0, tzinfo=eastern),
            dtend=datetime(2026, 1, 15, 11, 0, tzinfo=eastern),
        )
        result = ics_to_event_data(vevent)

        assert result["start_time"] == "15:00"
        assert result["end_time"] == "16:00"
        assert result["date"] == date(2026, 1, 15)

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
        original = {
            "title": "Round Trip",
            "description": "Test desc",
            "date": date(2026, 6, 15),
            "start_time": "09:30",
            "end_time": "10:45",
            "all_day": False,
            "external_id": "rt-uid-1",
        }
        cal = event_data_to_ics(original)

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
