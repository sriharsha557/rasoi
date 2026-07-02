"""
Tests for Recipe Parser.

Tests the RecipeParser class for parsing Text API responses into
structured recipe data, pretty-printing back to JSON, and validating
round-trip consistency.

Validates: Requirements 4.5, 13.1, 13.2, 13.4, 13.5
"""

import pytest
import json
from datetime import date
from hypothesis import given, strategies as st, settings, assume

from app.utils.recipe_parser import RecipeParser, RecipeParseError


class TestRecipeParserParse:
    """Tests for RecipeParser.parse() method."""
    
    def test_parse_valid_single_recipe(self):
        """Test parsing a single valid recipe."""
        response = json.dumps([{
            "name": "Pasta Tomato",
            "ingredients": [
                {"name": "pasta", "quantity": 400.0, "unit": "g", "available": True},
                {"name": "tomato", "quantity": 4.0, "unit": "pcs", "available": True},
                {"name": "basil", "quantity": 1.0, "unit": "bunch", "available": False}
            ],
            "steps": [
                "Boil water",
                "Add pasta",
                "Cook for 10 minutes",
                "Drain"
            ],
            "prepTimeMinutes": 25,
            "matchPercentage": 66.67,
            "usesExpiringItems": False,
            "missingIngredients": ["basil"]
        }])
        
        result = RecipeParser.parse(response)
        
        assert len(result) == 1
        assert result[0]["name"] == "Pasta Tomato"
        assert len(result[0]["ingredients"]) == 3
        assert len(result[0]["steps"]) == 4
        assert result[0]["prepTimeMinutes"] == 25
        assert result[0]["matchPercentage"] == 66.67
    
    def test_parse_multiple_recipes(self):
        """Test parsing multiple recipes."""
        response = json.dumps([
            {
                "name": "Recipe 1",
                "ingredients": [{"name": "ing1", "quantity": 1.0, "unit": "unit", "available": True}],
                "steps": ["Step 1", "Step 2"],
                "prepTimeMinutes": 30
            },
            {
                "name": "Recipe 2",
                "ingredients": [{"name": "ing2", "quantity": 2.0, "unit": "unit", "available": False}],
                "steps": ["Step 1", "Step 2", "Step 3"],
                "prepTimeMinutes": 45
            }
        ])
        
        result = RecipeParser.parse(response)
        
        assert len(result) == 2
        assert result[0]["name"] == "Recipe 1"
        assert result[1]["name"] == "Recipe 2"
    
    def test_parse_empty_list(self):
        """Test parsing empty recipe list."""
        response = json.dumps([])
        
        result = RecipeParser.parse(response)
        
        assert result == []
    
    def test_parse_malformed_json_raises_error(self):
        """Test that malformed JSON raises RecipeParseError."""
        response = "{ invalid json }"
        
        with pytest.raises(RecipeParseError) as exc_info:
            RecipeParser.parse(response)
        
        assert "Invalid JSON" in str(exc_info.value)
    
    def test_parse_non_list_json_raises_error(self):
        """Test that non-list JSON raises RecipeParseError."""
        response = json.dumps({"name": "recipe"})
        
        with pytest.raises(RecipeParseError) as exc_info:
            RecipeParser.parse(response)
        
        assert "must be a JSON array" in str(exc_info.value)
    
    def test_parse_missing_required_field_name(self):
        """Test that missing name field is skipped gracefully."""
        response = json.dumps([{
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []
    
    def test_parse_missing_required_field_ingredients(self):
        """Test that missing ingredients field is skipped gracefully."""
        response = json.dumps([{
            "name": "Recipe",
            "steps": ["Step 1"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []
    
    def test_parse_missing_required_field_steps(self):
        """Test that missing steps field is skipped gracefully."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []
    
    def test_parse_empty_recipe_name_is_skipped(self):
        """Test that empty recipe name is skipped gracefully."""
        response = json.dumps([{
            "name": "",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []
    
    def test_parse_recipe_with_no_ingredients_is_skipped(self):
        """Test that recipes with no ingredients are skipped."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [],
            "steps": ["Step 1"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []
    
    def test_parse_recipe_with_no_steps_is_skipped(self):
        """Test that recipes with no steps are skipped."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": [],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []
    
    def test_parse_recipe_with_minimum_ingredients(self):
        """Test parsing recipe with 3 minimum ingredients."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [
                {"name": "ing1", "quantity": 1.0, "unit": "unit", "available": True},
                {"name": "ing2", "quantity": 2.0, "unit": "unit", "available": True},
                {"name": "ing3", "quantity": 3.0, "unit": "unit", "available": True}
            ],
            "steps": ["Step 1"],
            "prepTimeMinutes": 20
        }])
        
        result = RecipeParser.parse(response)
        
        assert len(result) == 1
        assert len(result[0]["ingredients"]) == 3
    
    def test_parse_recipe_with_minimum_steps(self):
        """Test parsing recipe with 4 minimum steps."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        
        assert len(result) == 1
        assert len(result[0]["steps"]) == 4
    
    def test_parse_invalid_match_percentage_defaults_to_zero(self):
        """Test that invalid match percentage defaults to 0."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1"],
            "prepTimeMinutes": 30,
            "matchPercentage": 150  # Invalid - should be 0-100
        }])
        
        result = RecipeParser.parse(response)
        
        assert result[0]["matchPercentage"] == 0.0
    
    def test_parse_missing_ingredient_field_name(self):
        """Test that ingredient missing name is skipped."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [
                {"quantity": 1.0, "unit": "unit", "available": True}
            ],
            "steps": ["Step 1"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []  # Invalid ingredient causes recipe to be skipped
    
    def test_parse_negative_prep_time_is_skipped(self):
        """Test that negative prep time is skipped gracefully."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1"],
            "prepTimeMinutes": -30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []
    
    def test_parse_zero_prep_time_is_valid(self):
        """Test that zero prep time is valid."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1"],
            "prepTimeMinutes": 0
        }])
        
        result = RecipeParser.parse(response)
        assert len(result) == 1
        assert result[0]["prepTimeMinutes"] == 0


class TestRecipeParserPrettyPrint:
    """Tests for RecipeParser.pretty_print() method."""
    
    def test_pretty_print_single_recipe(self):
        """Test pretty-printing a single recipe."""
        recipes = [{
            "id": "recipe-1",
            "name": "Pasta",
            "ingredients": [{"name": "pasta", "quantity": 400.0, "unit": "g", "available": True}],
            "steps": ["Boil water", "Add pasta", "Cook", "Drain"],
            "prepTimeMinutes": 25,
            "matchPercentage": 100.0,
            "usesExpiringItems": False,
            "missingIngredients": [],
            "cuisine": "Italian",
            "difficulty": "Easy"
        }]
        
        result = RecipeParser.pretty_print(recipes)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "Pasta"
    
    def test_pretty_print_multiple_recipes(self):
        """Test pretty-printing multiple recipes."""
        recipes = [
            {
                "id": "recipe-1",
                "name": "Recipe 1",
                "ingredients": [{"name": "ing1", "quantity": 1.0, "unit": "unit", "available": True}],
                "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
                "prepTimeMinutes": 30,
                "matchPercentage": 100.0,
                "usesExpiringItems": False,
                "missingIngredients": []
            },
            {
                "id": "recipe-2",
                "name": "Recipe 2",
                "ingredients": [{"name": "ing2", "quantity": 2.0, "unit": "unit", "available": True}],
                "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
                "prepTimeMinutes": 45,
                "matchPercentage": 50.0,
                "usesExpiringItems": True,
                "missingIngredients": ["ing3"]
            }
        ]
        
        result = RecipeParser.pretty_print(recipes)
        
        parsed = json.loads(result)
        assert len(parsed) == 2
    
    def test_pretty_print_empty_list(self):
        """Test pretty-printing empty recipe list."""
        recipes = []
        
        result = RecipeParser.pretty_print(recipes)
        
        parsed = json.loads(result)
        assert parsed == []
    
    def test_pretty_print_produces_valid_json(self):
        """Test that output is valid JSON."""
        recipes = [{
            "id": "recipe-1",
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
            "prepTimeMinutes": 30,
            "matchPercentage": 100.0,
            "usesExpiringItems": False,
            "missingIngredients": []
        }]
        
        result = RecipeParser.pretty_print(recipes)
        
        # Should not raise
        json.loads(result)
    
    def test_pretty_print_includes_required_fields(self):
        """Test that all required fields are in output."""
        recipes = [{
            "id": "recipe-1",
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
            "prepTimeMinutes": 30,
            "matchPercentage": 75.0,
            "usesExpiringItems": True,
            "missingIngredients": ["missing"]
        }]
        
        result = RecipeParser.pretty_print(recipes)
        parsed = json.loads(result)
        
        item = parsed[0]
        assert "id" in item
        assert "name" in item
        assert "ingredients" in item
        assert "steps" in item
        assert "prepTimeMinutes" in item
        assert "matchPercentage" in item
        assert "usesExpiringItems" in item
        assert "missingIngredients" in item


class TestRecipeParserRoundTrip:
    """Tests for round-trip consistency: parse → pretty_print → parse."""
    
    def test_round_trip_single_recipe(self):
        """Test round-trip consistency with single recipe."""
        original_json = json.dumps([{
            "name": "Pasta Tomato",
            "ingredients": [
                {"name": "pasta", "quantity": 400.0, "unit": "g", "available": True},
                {"name": "tomato", "quantity": 4.0, "unit": "pcs", "available": False}
            ],
            "steps": ["Boil water", "Add pasta", "Cook", "Drain"],
            "prepTimeMinutes": 25,
            "matchPercentage": 50.0,
            "usesExpiringItems": True,
            "missingIngredients": ["basil"]
        }])
        
        # Parse
        parsed_1 = RecipeParser.parse(original_json)
        
        # Pretty-print
        serialized = RecipeParser.pretty_print(parsed_1)
        
        # Parse again
        parsed_2 = RecipeParser.parse(serialized)
        
        # Should be equivalent
        assert len(parsed_1) == len(parsed_2)
        assert parsed_1[0]["name"] == parsed_2[0]["name"]
        assert len(parsed_1[0]["ingredients"]) == len(parsed_2[0]["ingredients"])
        assert len(parsed_1[0]["steps"]) == len(parsed_2[0]["steps"])
        assert parsed_1[0]["prepTimeMinutes"] == parsed_2[0]["prepTimeMinutes"]
    
    def test_round_trip_multiple_recipes(self):
        """Test round-trip with multiple recipes."""
        original_json = json.dumps([
            {
                "name": "Recipe 1",
                "ingredients": [{"name": "ing1", "quantity": 1.0, "unit": "unit", "available": True}],
                "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
                "prepTimeMinutes": 30
            },
            {
                "name": "Recipe 2",
                "ingredients": [{"name": "ing2", "quantity": 2.0, "unit": "unit", "available": False}],
                "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
                "prepTimeMinutes": 45
            }
        ])
        
        parsed_1 = RecipeParser.parse(original_json)
        serialized = RecipeParser.pretty_print(parsed_1)
        parsed_2 = RecipeParser.parse(serialized)
        
        assert len(parsed_1) == len(parsed_2)
        for r1, r2 in zip(parsed_1, parsed_2):
            assert r1["name"] == r2["name"]
            assert len(r1["ingredients"]) == len(r2["ingredients"])
            assert len(r1["steps"]) == len(r2["steps"])
    
    def test_round_trip_empty_list(self):
        """Test round-trip with empty recipe list."""
        original_json = json.dumps([])
        
        parsed_1 = RecipeParser.parse(original_json)
        serialized = RecipeParser.pretty_print(parsed_1)
        parsed_2 = RecipeParser.parse(serialized)
        
        assert parsed_1 == []
        assert parsed_2 == []
    
    def test_round_trip_property_test(self):
        """Test the dedicated round_trip_test method."""
        test_json = json.dumps([{
            "name": "Complex Recipe",
            "ingredients": [
                {"name": "ingredient1", "quantity": 2.5, "unit": "cups", "available": True},
                {"name": "ingredient2", "quantity": 1.0, "unit": "tbsp", "available": False},
                {"name": "ingredient3", "quantity": 500.0, "unit": "g", "available": True}
            ],
            "steps": ["Prepare", "Cook", "Season", "Serve"],
            "prepTimeMinutes": 45,
            "matchPercentage": 66.67,
            "usesExpiringItems": True,
            "missingIngredients": ["ingredient2"]
        }])
        
        result = RecipeParser.round_trip_test(test_json)
        
        assert result is True
    
    def test_round_trip_with_various_step_counts(self):
        """Test round-trip with various step counts."""
        for step_count in [4, 5, 6, 7, 10]:
            steps = [f"Step {i+1}" for i in range(step_count)]
            
            original_json = json.dumps([{
                "name": "Recipe",
                "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
                "steps": steps,
                "prepTimeMinutes": 30
            }])
            
            parsed_1 = RecipeParser.parse(original_json)
            serialized = RecipeParser.pretty_print(parsed_1)
            parsed_2 = RecipeParser.parse(serialized)
            
            assert len(parsed_1[0]["steps"]) == len(parsed_2[0]["steps"]) == step_count


class TestRecipeParserErrorHandling:
    """Tests for error handling and edge cases."""
    
    def test_empty_recipe_name_after_strip_is_skipped(self):
        """Test that recipe name that is only whitespace is skipped."""
        response = json.dumps([{
            "name": "   ",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []
    
    def test_non_dict_item_in_list_is_skipped(self):
        """Test that non-dict items in list are skipped gracefully."""
        response = json.dumps(["not a dict"])
        
        result = RecipeParser.parse(response)
        assert result == []
    
    def test_prep_time_as_string_is_converted(self):
        """Test that string prep time is converted to int."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1"],
            "prepTimeMinutes": "30"
        }])
        
        result = RecipeParser.parse(response)
        
        assert result[0]["prepTimeMinutes"] == 30
    
    def test_invalid_prep_time_string_is_skipped(self):
        """Test that invalid prep time string is skipped gracefully."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1"],
            "prepTimeMinutes": "not a number"
        }])
        
        result = RecipeParser.parse(response)
        assert result == []
    
    def test_mixed_valid_and_invalid_recipes(self):
        """Test that valid recipes are parsed and invalid ones skipped."""
        response = json.dumps([
            {
                "name": "Recipe 1",
                "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
                "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
                "prepTimeMinutes": 30
            },
            {
                "name": "",  # Invalid - empty name
                "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
                "steps": ["Step 1"],
                "prepTimeMinutes": 20
            },
            {
                "name": "Recipe 2",
                "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
                "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
                "prepTimeMinutes": 45
            }
        ])
        
        result = RecipeParser.parse(response)
        
        assert len(result) == 2
        assert result[0]["name"] == "Recipe 1"
        assert result[1]["name"] == "Recipe 2"
    
    def test_whitespace_only_steps_are_filtered(self):
        """Test that whitespace-only steps are filtered out."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1", "   ", "Step 2", "Step 3"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        
        assert len(result[0]["steps"]) == 3  # Whitespace-only step filtered out
    
    def test_ingredient_with_invalid_quantity_is_skipped(self):
        """Test that ingredient with invalid quantity causes recipe to be skipped."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [
                {"name": "ing1", "quantity": 1.0, "unit": "unit", "available": True},
                {"name": "ing2", "quantity": -2.0, "unit": "unit", "available": True}
            ],
            "steps": ["Step 1"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []  # Invalid ingredient causes recipe to be skipped
    
    def test_ingredient_with_missing_unit_is_skipped(self):
        """Test that ingredient missing unit causes recipe to be skipped."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [
                {"name": "ing", "quantity": 1.0, "available": True}
            ],
            "steps": ["Step 1"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []  # Invalid ingredient causes recipe to be skipped
    
    def test_ingredient_empty_unit_is_skipped(self):
        """Test that ingredient with empty unit is skipped."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [
                {"name": "ing", "quantity": 1.0, "unit": "", "available": True}
            ],
            "steps": ["Step 1"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        assert result == []  # Invalid ingredient causes recipe to be skipped


class TestRecipeParserFieldExtraction:
    """Tests for correct field extraction - Property 13: Recipe Field Extraction."""
    
    def test_extract_recipe_name_field(self):
        """Test extracting recipe name field."""
        response = json.dumps([{
            "name": "Spaghetti Carbonara",
            "ingredients": [{"name": "pasta", "quantity": 400.0, "unit": "g", "available": True}],
            "steps": ["Boil", "Cook", "Drain", "Serve"],
            "prepTimeMinutes": 25
        }])
        
        result = RecipeParser.parse(response)
        
        assert "name" in result[0]
        assert isinstance(result[0]["name"], str)
        assert result[0]["name"] == "Spaghetti Carbonara"
    
    def test_extract_ingredients_field(self):
        """Test extracting ingredients field."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [
                {"name": "ing1", "quantity": 1.0, "unit": "cup", "available": True},
                {"name": "ing2", "quantity": 2.0, "unit": "tbsp", "available": False}
            ],
            "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
            "prepTimeMinutes": 30
        }])
        
        result = RecipeParser.parse(response)
        
        assert "ingredients" in result[0]
        assert isinstance(result[0]["ingredients"], list)
        assert len(result[0]["ingredients"]) == 2
    
    def test_extract_steps_field(self):
        """Test extracting steps field."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Prepare ingredients", "Cook", "Season", "Serve"],
            "prepTimeMinutes": 40
        }])
        
        result = RecipeParser.parse(response)
        
        assert "steps" in result[0]
        assert isinstance(result[0]["steps"], list)
        assert len(result[0]["steps"]) == 4
    
    def test_extract_prep_time_field(self):
        """Test extracting prep time field."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
            "prepTimeMinutes": 35
        }])
        
        result = RecipeParser.parse(response)
        
        assert "prepTimeMinutes" in result[0]
        assert isinstance(result[0]["prepTimeMinutes"], int)
        assert result[0]["prepTimeMinutes"] == 35
    
    def test_extract_ingredient_name_quantity_unit_available(self):
        """Test extracting all ingredient subfields."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [
                {
                    "name": "flour",
                    "quantity": 2.5,
                    "unit": "cups",
                    "available": True
                }
            ],
            "steps": ["Mix", "Bake", "Cool", "Serve"],
            "prepTimeMinutes": 60
        }])
        
        result = RecipeParser.parse(response)
        
        ing = result[0]["ingredients"][0]
        assert "name" in ing
        assert "quantity" in ing
        assert "unit" in ing
        assert "available" in ing
        assert ing["name"] == "flour"
        assert ing["quantity"] == 2.5
        assert ing["unit"] == "cups"
        assert ing["available"] is True
    
    def test_extract_optional_fields(self):
        """Test extracting optional fields when present."""
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
            "prepTimeMinutes": 30,
            "matchPercentage": 85.5,
            "usesExpiringItems": True,
            "missingIngredients": ["missing_ing"],
            "cuisine": "Italian",
            "difficulty": "Hard"
        }])
        
        result = RecipeParser.parse(response)
        
        assert result[0]["matchPercentage"] == 85.5
        assert result[0]["usesExpiringItems"] is True
        assert result[0]["missingIngredients"] == ["missing_ing"]
        assert result[0]["cuisine"] == "Italian"
        assert result[0]["difficulty"] == "Hard"


class TestRecipeParserPropertyTests:
    """Property-based tests for recipe parsing."""
    
    @settings(max_examples=10)
    @given(
        recipe_name=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cc", "Cs"))).filter(lambda x: x.strip()),
        num_ingredients=st.integers(min_value=3, max_value=10),
        num_steps=st.integers(min_value=4, max_value=10),
        prep_time=st.integers(min_value=5, max_value=180)
    )
    def test_recipe_parser_handles_varied_recipe_structures(
        self, recipe_name, num_ingredients, num_steps, prep_time
    ):
        """
        Property: Recipe parser can handle varied recipe structures with
        different numbers of ingredients and steps.
        
        Validates: Requirements 13.1, 13.2
        """
        # Build varied recipe structure
        ingredients = [
            {
                "name": f"ingredient_{i}",
                "quantity": float(i + 1),
                "unit": "unit",
                "available": i % 2 == 0
            }
            for i in range(num_ingredients)
        ]
        
        steps = [f"Step {i+1}" for i in range(num_steps)]
        
        response = json.dumps([{
            "name": recipe_name,
            "ingredients": ingredients,
            "steps": steps,
            "prepTimeMinutes": prep_time
        }])
        
        result = RecipeParser.parse(response)
        
        assert len(result) == 1
        # After parsing, whitespace is stripped from recipe name
        assert result[0]["name"] == recipe_name.strip()
        assert len(result[0]["ingredients"]) == num_ingredients
        assert len(result[0]["steps"]) == num_steps
        assert result[0]["prepTimeMinutes"] == prep_time
    
    @settings(max_examples=10)
    @given(
        match_percentage=st.floats(min_value=0.0, max_value=100.0)
    )
    def test_recipe_parser_preserves_match_percentage(self, match_percentage):
        """
        Property: Recipe parser correctly preserves match percentage values
        within valid range (0-100).
        
        Validates: Requirements 13.2, 13.4
        """
        response = json.dumps([{
            "name": "Recipe",
            "ingredients": [{"name": "ing", "quantity": 1.0, "unit": "unit", "available": True}],
            "steps": ["Step 1", "Step 2", "Step 3", "Step 4"],
            "prepTimeMinutes": 30,
            "matchPercentage": match_percentage
        }])
        
        result = RecipeParser.parse(response)
        
        assert len(result) == 1
        assert 0.0 <= result[0]["matchPercentage"] <= 100.0
        assert result[0]["matchPercentage"] == match_percentage


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
