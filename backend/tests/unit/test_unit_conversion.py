"""Unit tests for the unit conversion system (constants/units.py)."""

import pytest
from app.constants.units import (
    VALID_UNITS,
    UNIT_TO_GROUP,
    to_base_unit,
    from_base_unit,
    format_ingredient_title,
    normalize_unit,
)


class TestUnitValidation:
    """Tests for unit metadata and validation."""

    def test_valid_units_list(self):
        assert "lb" in VALID_UNITS
        assert "cup" in VALID_UNITS
        assert "clove" in VALID_UNITS
        assert "handful" not in VALID_UNITS

    def test_unit_to_group(self):
        assert UNIT_TO_GROUP["lb"] == "weight"
        assert UNIT_TO_GROUP["cup"] == "volume"
        assert UNIT_TO_GROUP["clove"] == "count"

    def test_has_22_total_units(self):
        # 4 weight + 9 volume + 9 count = 22
        assert len(VALID_UNITS) == 22


class TestToBaseUnit:
    """Tests for to_base_unit()"""

    def test_lb_to_grams(self):
        qty, unit = to_base_unit(1, "lb")
        assert qty == pytest.approx(453.592)
        assert unit == "g"

    def test_oz_to_grams(self):
        qty, unit = to_base_unit(1, "oz")
        assert qty == pytest.approx(28.3495)
        assert unit == "g"

    def test_kg_to_grams(self):
        qty, unit = to_base_unit(2, "kg")
        assert qty == 2000
        assert unit == "g"

    def test_cup_to_ml(self):
        qty, unit = to_base_unit(1, "cup")
        assert qty == pytest.approx(236.588)
        assert unit == "ml"

    def test_tbsp_to_ml(self):
        qty, unit = to_base_unit(2, "tbsp")
        assert qty == pytest.approx(29.574)
        assert unit == "ml"

    def test_count_stays_as_is(self):
        qty, unit = to_base_unit(3, "clove")
        assert qty == 3
        assert unit == "clove"

    def test_unknown_unit_raises(self):
        with pytest.raises(ValueError):
            to_base_unit(1, "xyzzy")


class TestFromBaseUnit:
    """Tests for from_base_unit()"""

    def test_grams_to_imperial_lb_threshold(self):
        # 453.6g = 1 lb, stays as lb
        qty, unit = from_base_unit(453.6, "g", "imperial")
        assert unit == "lb"
        assert qty == pytest.approx(1.0, abs=0.1)

    def test_grams_to_imperial_oz_under_threshold(self):
        # 200g is under 1 lb → should display as oz
        qty, unit = from_base_unit(200, "g", "imperial")
        assert unit == "oz"

    def test_grams_to_metric_kg_threshold(self):
        # 1000g → 1 kg in metric
        qty, unit = from_base_unit(1000, "g", "metric")
        assert unit == "kg"
        assert qty == 1.0

    def test_grams_to_metric_g_under_threshold(self):
        # 500g stays as g in metric
        qty, unit = from_base_unit(500, "g", "metric")
        assert unit == "g"
        assert qty == 500.0

    def test_ml_to_imperial_cup_threshold(self):
        # 236.6ml = 1 cup
        qty, unit = from_base_unit(236.588, "ml", "imperial")
        assert unit == "cup"
        assert qty == pytest.approx(1.0, abs=0.1)

    def test_ml_to_metric_l_threshold(self):
        # 1000ml → 1 L in metric
        qty, unit = from_base_unit(1000, "ml", "metric")
        assert unit == "l"
        assert qty == 1.0


class TestFormatIngredientTitle:
    """Tests for format_ingredient_title()"""

    def test_standard_format(self):
        assert format_ingredient_title(2, "lb", "ground beef") == "2 lb ground beef"

    def test_decimal_quantity(self):
        assert format_ingredient_title(1.5, "cup", "flour") == "1.5 cup flour"

    def test_whole_number_drops_decimal(self):
        # 1.0 should display as "1", not "1.0"
        assert format_ingredient_title(1.0, "cup", "flour") == "1 cup flour"

    def test_no_quantity_just_name(self):
        assert format_ingredient_title(None, None, "olive oil") == "olive oil"

    def test_no_unit_just_name(self):
        assert format_ingredient_title(1, None, "salt") == "salt"


class TestNormalizeUnit:
    """Tests for normalize_unit() - freeform text mapping"""

    def test_exact_match(self):
        assert normalize_unit("lb") == "lb"
        assert normalize_unit("cup") == "cup"

    def test_case_insensitive(self):
        assert normalize_unit("LB") == "lb"
        assert normalize_unit("Cup") == "cup"

    def test_whitespace_trimming(self):
        assert normalize_unit("  lb  ") == "lb"

    def test_freeform_mapping(self):
        assert normalize_unit("pound") == "lb"
        assert normalize_unit("pounds") == "lb"
        assert normalize_unit("tablespoon") == "tbsp"
        assert normalize_unit("tablespoons") == "tbsp"
        assert normalize_unit("teaspoon") == "tsp"

    def test_unrecognized_returns_none(self):
        assert normalize_unit("handful") is None
        assert normalize_unit("dash") is None

    def test_none_and_empty(self):
        assert normalize_unit(None) is None
        assert normalize_unit("") is None


class TestRoundTripConversion:
    """Tests that verify values round-trip correctly."""

    def test_lb_round_trip_imperial(self):
        # 2 lb → base → imperial display → 2 lb
        base_qty, base_unit = to_base_unit(2, "lb")
        display_qty, display_unit = from_base_unit(base_qty, base_unit, "imperial")
        assert display_unit == "lb"
        assert display_qty == pytest.approx(2.0, abs=0.1)

    def test_lb_to_metric_round_trip(self):
        # 2 lb = 907.2g → displays as 907.2g in metric (under 1kg)
        base_qty, base_unit = to_base_unit(2, "lb")
        display_qty, display_unit = from_base_unit(base_qty, base_unit, "metric")
        assert display_unit == "g"
        assert display_qty == pytest.approx(907.2, abs=1.0)

    def test_addition_crossing_threshold(self):
        # 1 lb + 8 oz = 453.6g + 226.8g = 680.4g → 1.5 lb
        q1, _ = to_base_unit(1, "lb")
        q2, _ = to_base_unit(8, "oz")
        total = q1 + q2
        display_qty, display_unit = from_base_unit(total, "g", "imperial")
        assert display_unit == "lb"
        assert display_qty == pytest.approx(1.5, abs=0.1)
