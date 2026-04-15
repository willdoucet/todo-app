import pytest

from app.services.shopping_sync import canonicalize_name


class TestCanonicalizeName:
    """Tests for canonicalize_name() ingredient normalization."""

    # -- Basic normalization (lowercase, trim, collapse whitespace) -----------

    def test_lowercase(self):
        assert canonicalize_name("Bananas") == "banana"

    def test_trim_whitespace(self):
        assert canonicalize_name("  garlic  ") == "garlic"

    def test_collapse_internal_whitespace(self):
        assert canonicalize_name("  ground   beef  ") == "ground beef"

    def test_empty_string(self):
        assert canonicalize_name("") == ""

    # -- Irregular plurals (exact full-name match from table) -----------------

    def test_irregular_tomatoes(self):
        assert canonicalize_name("tomatoes") == "tomato"

    def test_irregular_potatoes(self):
        assert canonicalize_name("potatoes") == "potato"

    def test_irregular_leaves(self):
        assert canonicalize_name("leaves") == "leaf"

    def test_irregular_berries(self):
        assert canonicalize_name("berries") == "berry"

    def test_irregular_cherries(self):
        assert canonicalize_name("cherries") == "cherry"

    def test_irregular_strawberries(self):
        assert canonicalize_name("strawberries") == "strawberry"

    def test_irregular_bunches(self):
        assert canonicalize_name("bunches") == "bunch"

    def test_irregular_peaches(self):
        assert canonicalize_name("peaches") == "peach"

    # -- Last-word irregular plural in compound name --------------------------

    def test_compound_last_word_irregular(self):
        assert canonicalize_name("fresh tomatoes") == "fresh tomato"

    def test_compound_last_word_irregular_uppercase(self):
        assert canonicalize_name("Fresh Tomatoes") == "fresh tomato"

    # -- Regular plurals (suffix-stripping) -----------------------------------

    def test_regular_plural_bananas(self):
        assert canonicalize_name("bananas") == "banana"

    def test_regular_plural_apples(self):
        assert canonicalize_name("apples") == "apple"

    def test_regular_plural_carrots(self):
        assert canonicalize_name("carrots") == "carrot"

    # -- Compound names that should not change --------------------------------

    def test_compound_ground_beef(self):
        assert canonicalize_name("ground beef") == "ground beef"

    def test_compound_olive_oil(self):
        assert canonicalize_name("olive oil") == "olive oil"

    # -- No change needed (already singular / no plural suffix) ---------------

    def test_no_change_garlic(self):
        assert canonicalize_name("garlic") == "garlic"

    def test_no_change_rice(self):
        assert canonicalize_name("rice") == "rice"

    # -- Edge cases -----------------------------------------------------------

    def test_glass_not_stripped(self):
        """Words ending in 'ss' should NOT have an 's' stripped."""
        assert canonicalize_name("glass") == "glass"

    def test_bus_stripped(self):
        """Short word ending in 's' (not 'ss') gets stripped — known lossy."""
        assert canonicalize_name("bus") == "bu"

    def test_single_char(self):
        """Very short input should not crash or strip excessively."""
        assert canonicalize_name("a") == "a"

    def test_two_char_word_ending_in_s(self):
        """len('as') == 2 which is NOT > 2, so 's' is not stripped."""
        assert canonicalize_name("as") == "as"

    # -- Suffix-stripping: 'ies' → 'y' (len > 4) ----------------------------

    def test_ies_bodies(self):
        assert canonicalize_name("bodies") == "body"

    # -- Suffix-stripping: 'es' with sh/ch/x/z/ss stem ----------------------

    def test_es_boxes(self):
        assert canonicalize_name("boxes") == "box"

    def test_es_dishes(self):
        assert canonicalize_name("dishes") == "dish"

    # -- Suffix-stripping: 'es' without special stem (strip just 's') --------

    def test_es_plates(self):
        assert canonicalize_name("plates") == "plate"
