"""
Predefined unit system for recipe ingredients and shopping list aggregation.

Unit groups:
  - Weight: lb, oz, g, kg → base unit: grams (g)
  - Volume: cup, tbsp, tsp, ml, l, fl oz, quart, pint, gallon → base unit: milliliters (ml)
  - Count: piece, clove, slice, bunch, can, package, head, stalk, sprig → same-unit only
  - None: no unit (pantry staples like "olive oil", "salt")

Aggregation rules:
  - Units in the same group can be summed (convert to base, sum, convert back to display)
  - Units in different groups stay as separate shopping items
  - Count units only aggregate with the SAME unit (3 cloves + 2 cloves = 5 cloves)
  - "None" items deduplicate by name only
"""

# ── Unit group definitions ──

WEIGHT_UNITS = {
    "lb": {"name": "pound", "to_base": 453.592, "base": "g"},
    "oz": {"name": "ounce", "to_base": 28.3495, "base": "g"},
    "g": {"name": "gram", "to_base": 1.0, "base": "g"},
    "kg": {"name": "kilogram", "to_base": 1000.0, "base": "g"},
}

VOLUME_UNITS = {
    "cup": {"name": "cup", "to_base": 236.588, "base": "ml"},
    "tbsp": {"name": "tablespoon", "to_base": 14.787, "base": "ml"},
    "tsp": {"name": "teaspoon", "to_base": 4.929, "base": "ml"},
    "ml": {"name": "milliliter", "to_base": 1.0, "base": "ml"},
    "l": {"name": "liter", "to_base": 1000.0, "base": "ml"},
    "fl oz": {"name": "fluid ounce", "to_base": 29.5735, "base": "ml"},
    "quart": {"name": "quart", "to_base": 946.353, "base": "ml"},
    "pint": {"name": "pint", "to_base": 473.176, "base": "ml"},
    "gallon": {"name": "gallon", "to_base": 3785.41, "base": "ml"},
}

COUNT_UNITS = {
    "piece": {"name": "piece"},
    "clove": {"name": "clove"},
    "slice": {"name": "slice"},
    "bunch": {"name": "bunch"},
    "can": {"name": "can"},
    "package": {"name": "package"},
    "head": {"name": "head"},
    "stalk": {"name": "stalk"},
    "sprig": {"name": "sprig"},
}

# ── Lookup tables ──

# All valid unit abbreviations
ALL_UNITS = {**WEIGHT_UNITS, **VOLUME_UNITS, **COUNT_UNITS}

# Map unit abbreviation → group name
UNIT_TO_GROUP = {}
for unit in WEIGHT_UNITS:
    UNIT_TO_GROUP[unit] = "weight"
for unit in VOLUME_UNITS:
    UNIT_TO_GROUP[unit] = "volume"
for unit in COUNT_UNITS:
    UNIT_TO_GROUP[unit] = "count"

# Valid unit abbreviation list (for schema validation)
VALID_UNITS = list(ALL_UNITS.keys())

# ── Display preference mapping ──
# Which units to display for each group in imperial vs metric

IMPERIAL_DISPLAY = {
    "weight": ["lb", "oz"],
    "volume": ["cup", "tbsp", "tsp", "fl oz", "quart", "pint", "gallon"],
}

METRIC_DISPLAY = {
    "weight": ["kg", "g"],
    "volume": ["l", "ml"],
}

# ── Freeform unit migration mapping ──
# Maps common freeform text values to predefined units

FREEFORM_UNIT_MAP = {
    # Weight
    "pound": "lb", "pounds": "lb", "lbs": "lb",
    "ounce": "oz", "ounces": "oz",
    "gram": "g", "grams": "g",
    "kilogram": "kg", "kilograms": "kg", "kgs": "kg",
    # Volume
    "cup": "cup", "cups": "cup",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp": "tbsp", "tbs": "tbsp", "T": "tbsp",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsp": "tsp", "t": "tsp",
    "milliliter": "ml", "milliliters": "ml", "mL": "ml",
    "liter": "l", "liters": "l", "L": "l",
    "fluid ounce": "fl oz", "fluid ounces": "fl oz", "fl oz": "fl oz",
    "quart": "quart", "quarts": "quart", "qt": "quart",
    "pint": "pint", "pints": "pint", "pt": "pint",
    "gallon": "gallon", "gallons": "gallon", "gal": "gallon",
    # Count
    "piece": "piece", "pieces": "piece", "pc": "piece", "pcs": "piece",
    "clove": "clove", "cloves": "clove",
    "slice": "slice", "slices": "slice",
    "bunch": "bunch", "bunches": "bunch",
    "can": "can", "cans": "can",
    "package": "package", "packages": "package", "pkg": "package", "pkgs": "package",
    "head": "head", "heads": "head",
    "stalk": "stalk", "stalks": "stalk",
    "sprig": "sprig", "sprigs": "sprig",
}


# ── Conversion functions ──

def to_base_unit(quantity: float, unit: str) -> tuple[float, str]:
    """Convert a quantity + unit to its base unit (grams or ml).

    Returns (base_quantity, base_unit).
    Raises ValueError for count units (no cross-conversion).
    """
    group = UNIT_TO_GROUP.get(unit)
    if group == "weight":
        return quantity * WEIGHT_UNITS[unit]["to_base"], "g"
    elif group == "volume":
        return quantity * VOLUME_UNITS[unit]["to_base"], "ml"
    elif group == "count":
        return quantity, unit  # Count units stay as-is
    else:
        raise ValueError(f"Unknown unit: {unit}")


def from_base_unit(base_quantity: float, base_unit: str, system: str = "imperial") -> tuple[float, str]:
    """Convert from base unit (g or ml) to the best display unit for the given system.

    Args:
        base_quantity: Quantity in base units (grams or ml)
        base_unit: "g" or "ml"
        system: "imperial" or "metric"

    Returns (display_quantity, display_unit).
    """
    if base_unit == "g":
        units = WEIGHT_UNITS
        if system == "metric":
            # Use kg for >= 1000g, else g
            if base_quantity >= 1000:
                return round(base_quantity / 1000, 1), "kg"
            return round(base_quantity, 1), "g"
        else:
            # Imperial: use lb for >= 453.6g (1 lb), else oz
            if base_quantity >= 453.592:
                return round(base_quantity / 453.592, 1), "lb"
            return round(base_quantity / 28.3495, 1), "oz"
    elif base_unit == "ml":
        if system == "metric":
            # Use l for >= 1000ml, else ml
            if base_quantity >= 1000:
                return round(base_quantity / 1000, 1), "l"
            return round(base_quantity, 1), "ml"
        else:
            # Imperial: use cups for >= 1 cup, tbsp for >= 1 tbsp, else tsp
            if base_quantity >= 236.588:
                return round(base_quantity / 236.588, 1), "cup"
            elif base_quantity >= 14.787:
                return round(base_quantity / 14.787, 1), "tbsp"
            return round(base_quantity / 4.929, 1), "tsp"
    else:
        # Count unit — return as-is
        return round(base_quantity), base_unit


def format_ingredient_title(quantity: float | None, unit: str | None, name: str) -> str:
    """Format an ingredient as a shopping list task title.

    Examples:
        format_ingredient_title(2, "lb", "ground beef") → "2 lb ground beef"
        format_ingredient_title(1.5, "cup", "flour") → "1.5 cup flour"
        format_ingredient_title(None, None, "olive oil") → "olive oil"
        format_ingredient_title(3, "clove", "garlic") → "3 clove garlic"
    """
    if quantity is None or unit is None:
        return name
    # Format quantity: drop .0 for whole numbers
    if quantity == int(quantity):
        qty_str = str(int(quantity))
    else:
        qty_str = str(round(quantity, 1))
    return f"{qty_str} {unit} {name}"


def normalize_unit(freeform: str | None) -> str | None:
    """Map a freeform unit string to a predefined unit abbreviation.

    Returns None if the input is None, empty, or unrecognized.
    """
    if not freeform:
        return None
    cleaned = freeform.strip().lower()
    # Direct match
    if cleaned in ALL_UNITS:
        return cleaned
    # Freeform mapping
    return FREEFORM_UNIT_MAP.get(cleaned)
