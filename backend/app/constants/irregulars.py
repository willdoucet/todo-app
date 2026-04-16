"""Irregular plural → singular mappings for ingredient name canonicalization.

Used by shopping_sync.canonicalize_name() to normalize plurals before
aggregation matching. Only covers common food-related irregulars that
the simple suffix-stripping rules (remove trailing 's'/'es'/'ies') miss.
"""

# Maps lowercase plural → lowercase singular
IRREGULAR_PLURALS = {
    "tomatoes": "tomato",
    "potatoes": "potato",
    "leaves": "leaf",
    "knives": "knife",
    "loaves": "loaf",
    "halves": "half",
    "berries": "berry",
    "cherries": "cherry",
    "strawberries": "strawberry",
    "blueberries": "blueberry",
    "raspberries": "raspberry",
    "blackberries": "blackberry",
    "cranberries": "cranberry",
    "anchovies": "anchovy",
    "peaches": "peach",
    "radishes": "radish",
    "squashes": "squash",
    "bunches": "bunch",
    "batches": "batch",
    "sandwiches": "sandwich",
    "tortillas": "tortilla",
}
