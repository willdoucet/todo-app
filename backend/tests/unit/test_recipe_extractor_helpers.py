"""Unit tests for the private helpers inside ``app.services.recipe_extractor``.

These helpers compose the public ``extract_recipe`` pipeline. Each one is
deterministic and pure (no Celery, no real HTTP, no real Anthropic) so we
exercise them directly with hand-crafted inputs.
"""
from __future__ import annotations

import json

import pytest

from app.services import recipe_extractor as re


# ---------------------------------------------------------------------------
# _clean_and_budget
# ---------------------------------------------------------------------------


class TestCleanAndBudget:
    def test_strips_script_style_nav_footer(self):
        html = """
        <html>
          <head><style>body { color: red }</style></head>
          <body>
            <nav>navigation menu blah blah</nav>
            <article>The real content lives here.</article>
            <footer>copyright bla bla</footer>
            <script>alert('xss')</script>
          </body>
        </html>
        """
        cleaned = re._clean_and_budget(html)
        assert "The real content lives here." in cleaned
        assert "alert('xss')" not in cleaned
        assert "navigation menu" not in cleaned
        assert "color: red" not in cleaned
        assert "copyright" not in cleaned

    def test_preserves_jsonld_blocks(self):
        recipe_jsonld = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "Recipe",
                "name": "Spaghetti Carbonara",
                "recipeIngredient": ["200g spaghetti", "2 eggs"],
            }
        )
        html = f"""
        <html><body>
          <script type="application/ld+json">{recipe_jsonld}</script>
          <article>Some prose about pasta.</article>
        </body></html>
        """
        cleaned = re._clean_and_budget(html)
        # JSON-LD should appear verbatim in the output budget.
        assert "Spaghetti Carbonara" in cleaned
        assert "recipeIngredient" in cleaned
        assert "# JSON-LD" in cleaned

    def test_budget_caps_output_at_24kb(self):
        # Construct an HTML body well over 24 KB.
        body = "lorem ipsum dolor sit amet " * 5000  # ~135 KB raw
        html = f"<html><body><article>{body}</article></body></html>"
        cleaned = re._clean_and_budget(html)
        assert len(cleaned.encode("utf-8")) <= 24 * 1024

    def test_custom_max_bytes_respected(self):
        body = "x" * 10_000
        html = f"<html><body><article>{body}</article></body></html>"
        cleaned = re._clean_and_budget(html, max_bytes=1024)
        assert len(cleaned.encode("utf-8")) <= 1024

    def test_survives_nested_ad_with_class_bearing_descendants(self):
        """Regression: bs4 4.14+ nulls `attrs` on descendants when an ancestor
        is decomposed. `find_all` returns an eager list, so decomposing an ad
        container mid-iteration leaves stale descendant references whose
        `attrs` is None — an unguarded `tag.get("class", [])` crashed with
        AttributeError on real pages like seriouseats.com. The helper must
        tolerate these stale references and still emit cleaned content.
        """
        html = """
        <html><body>
          <div class="ad-slot">
            <div class="inner-card">
              <span class="title">ad content that must be stripped</span>
            </div>
          </div>
          <article class="content">Real recipe content lives in here.</article>
        </body></html>
        """
        cleaned = re._clean_and_budget(html)
        assert "Real recipe content lives in here." in cleaned
        assert "ad content that must be stripped" not in cleaned

    def test_tolerates_class_attribute_as_string(self):
        """Some parsers/edge cases surface `class` as a single string rather
        than a list. Guard against that too."""
        html = '<html><body><article class="advertisement">should drop</article>'\
               '<article class="main">keep me</article></body></html>'
        cleaned = re._clean_and_budget(html)
        assert "keep me" in cleaned
        assert "should drop" not in cleaned


# ---------------------------------------------------------------------------
# _validate_semantics
# ---------------------------------------------------------------------------


def _valid_llm_recipe(**overrides) -> re._LlmRecipe:
    """Build an LLM recipe that passes _validate_semantics by default."""
    base = dict(
        name="Honey Garlic Chicken",
        description="A weeknight win.",
        ingredients=[
            re._LlmIngredient(name="chicken breast", quantity=2.0, unit="lb", category="Protein"),
            re._LlmIngredient(name="honey", quantity=0.25, unit="cup", category="Pantry"),
        ],
        instructions=(
            "1. Season chicken. 2. Cook in pan. 3. Add sauce and reduce. "
            "4. Serve hot over rice."
        ),
        prep_time_minutes=10,
        cook_time_minutes=20,
        servings=4,
        tags=["chicken", "weeknight"],
    )
    base.update(overrides)
    return re._LlmRecipe(**base)


class TestValidateSemantics:
    def test_valid_recipe_passes(self):
        recipe = _valid_llm_recipe()
        # Should not raise.
        re._validate_semantics(recipe, cleaned_content="ordinary recipe page text")

    def test_empty_name_raises_not_recipe(self):
        recipe = _valid_llm_recipe(name=" ")
        with pytest.raises(re.NotRecipe):
            re._validate_semantics(recipe, cleaned_content="ordinary content")

    def test_too_few_ingredients_raises_not_recipe(self):
        recipe = _valid_llm_recipe(
            ingredients=[
                re._LlmIngredient(name="chicken", quantity=1, unit="lb", category="Protein"),
            ]
        )
        with pytest.raises(re.NotRecipe):
            re._validate_semantics(recipe, cleaned_content="ordinary content")

    def test_trivial_instructions_raises_not_recipe(self):
        recipe = _valid_llm_recipe(instructions="cook")
        with pytest.raises(re.NotRecipe):
            re._validate_semantics(recipe, cleaned_content="ordinary content")

    def test_missing_instructions_raises_not_recipe(self):
        recipe = _valid_llm_recipe(instructions=None)
        with pytest.raises(re.NotRecipe):
            re._validate_semantics(recipe, cleaned_content="ordinary content")

    def test_interstitial_javascript_phrase_raises(self):
        recipe = _valid_llm_recipe()
        with pytest.raises(re.NotRecipe):
            re._validate_semantics(
                recipe,
                cleaned_content="please enable javascript to view this site",
            )

    def test_interstitial_human_check_raises(self):
        recipe = _valid_llm_recipe()
        with pytest.raises(re.NotRecipe):
            re._validate_semantics(
                recipe,
                cleaned_content="we need to verify you are human before continuing",
            )


# ---------------------------------------------------------------------------
# _normalize_to_recipe_detail
# ---------------------------------------------------------------------------


class TestNormalizeToRecipeDetail:
    def test_valid_data_passes_through(self):
        recipe = _valid_llm_recipe()
        out = re._normalize_to_recipe_detail(recipe, source_url="https://x.example/r")
        assert out.source_url == "https://x.example/r"
        assert out.servings == 4
        assert len(out.ingredients) == 2
        assert out.ingredients[0].unit == "lb"

    def test_bad_units_get_coerced_to_none(self):
        recipe = _valid_llm_recipe(
            ingredients=[
                # "handful" is not in VALID_UNITS — must be coerced to None.
                re._LlmIngredient(name="parsley", quantity=1, unit="handful", category="Produce"),
                re._LlmIngredient(name="salt", quantity=1, unit="tsp", category="Pantry"),
            ]
        )
        out = re._normalize_to_recipe_detail(recipe, source_url="https://x.example/")
        assert out.ingredients[0].unit is None
        assert out.ingredients[1].unit == "tsp"

    def test_unknown_category_becomes_other(self):
        recipe = _valid_llm_recipe(
            ingredients=[
                re._LlmIngredient(
                    name="kombu", quantity=1, unit="oz", category="MisleadingCategory"
                ),
                re._LlmIngredient(name="rice", quantity=1, unit="cup", category="Pantry"),
            ]
        )
        out = re._normalize_to_recipe_detail(recipe, source_url="https://x.example/")
        assert out.ingredients[0].category == "Other"
        assert out.ingredients[1].category == "Pantry"
