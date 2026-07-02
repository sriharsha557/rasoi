"""
Tests for Ingredient Parser.

Tests the IngredientParser class for parsing Vision API responses into
structured ingredient data, pretty-printing back to JSON, and validating
round-trip consistency.

Validates: Requirements 1.6, 12.1, 12.2, 12.4, 12.5
"""

import pytest
import json
from datetime import date, timedelta
from app.utils.ingredient_parser import IngredientParser, IngredientParseError


class TestIngredientParserParse:
    """Tests for IngredientParser.parse() method."""
    
    def test_parse_valid_single_ingredient(self):
        """Test parsing a single valid ingredient."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25",
            "confidence": 0.95
        }])
        
        result = IngredientParser.parse(response)
        
        assert len(result) == 1
        assert result[0]["name"] == "tomato"
        assert result[0]["quantity"] == 2.0
        assert result[0]["unit"] == "pcs"
        assert result[0]["acquisition_date"] == "2024-01-15"
        assert result[0]["expiration_date"] == "2024-01-25"
        assert result[0]["confidence"] == 0.95
    
    def test_parse_multiple_ingredients(self):
        """Test parsing multiple ingredients."""
        response = json.dumps([
            {
                "name": "tomato",
                "quantity": 2.0,
                "unit": "pcs",
                "acquisition_date": "2024-01-15",
                "expiration_date": "2024-01-25",
                "confidence": 0.95
            },
            {
                "name": "lettuce",
                "quantity": 1.0,
                "unit": "head",
                "acquisition_date": "2024-01-16",
                "expiration_date": "2024-01-22",
                "confidence": 0.92
            }
        ])
        
        result = IngredientParser.parse(response)
        
        assert len(result) == 2
        assert result[0]["name"] == "tomato"
        assert result[1]["name"] == "lettuce"
    
    def test_parse_optional_confidence_field(self):
        """Test that confidence field is optional with default of 1.0."""
        response = json.dumps([{
            "name": "onion",
            "quantity": 1.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-30"
        }])
        
        result = IngredientParser.parse(response)
        
        assert len(result) == 1
        assert result[0]["confidence"] == 1.0
    
    def test_parse_empty_list(self):
        """Test parsing empty ingredient list."""
        response = json.dumps([])
        
        result = IngredientParser.parse(response)
        
        assert result == []
    
    def test_parse_malformed_json_raises_error(self):
        """Test that malformed JSON raises IngredientParseError."""
        response = "{ invalid json }"
        
        with pytest.raises(IngredientParseError) as exc_info:
            IngredientParser.parse(response)
        
        assert "Invalid JSON" in str(exc_info.value)
    
    def test_parse_non_list_json_raises_error(self):
        """Test that non-list JSON raises IngredientParseError."""
        response = json.dumps({"name": "tomato"})
        
        with pytest.raises(IngredientParseError) as exc_info:
            IngredientParser.parse(response)
        
        assert "must be a JSON array" in str(exc_info.value)
    
    def test_parse_missing_required_field_name(self):
        """Test that missing name field is skipped gracefully."""
        response = json.dumps([{
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        # Should skip the invalid item and return empty list
        result = IngredientParser.parse(response)
        assert result == []
    
    def test_parse_missing_required_field_date(self):
        """Test that missing acquisition_date is skipped gracefully."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": 2.0,
            "unit": "pcs",
            "expiration_date": "2024-01-25"
        }])
        
        # Should skip the invalid item and return empty list
        result = IngredientParser.parse(response)
        assert result == []
    
    def test_parse_invalid_date_format(self):
        """Test that invalid date format is skipped gracefully."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "01/15/2024",
            "expiration_date": "2024-01-25"
        }])
        
        # Should skip the invalid item and return empty list
        result = IngredientParser.parse(response)
        assert result == []
    
    def test_parse_negative_quantity_is_skipped(self):
        """Test that negative quantity is skipped gracefully."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": -2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        # Should skip the invalid item and return empty list
        result = IngredientParser.parse(response)
        assert result == []
    
    def test_parse_zero_quantity_is_valid(self):
        """Test that zero quantity is valid."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": 0.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        
        assert len(result) == 1
        assert result[0]["quantity"] == 0.0
    
    def test_parse_normalizes_name_to_lowercase(self):
        """Test that ingredient names are normalized to lowercase."""
        response = json.dumps([{
            "name": "TOMATO",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        
        assert result[0]["name"] == "tomato"
    
    def test_parse_strips_whitespace_from_name(self):
        """Test that whitespace is stripped from names."""
        response = json.dumps([{
            "name": "  tomato  ",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        
        assert result[0]["name"] == "tomato"
    
    def test_parse_with_fractional_quantity(self):
        """Test parsing with fractional quantities."""
        response = json.dumps([{
            "name": "salt",
            "quantity": 0.5,
            "unit": "tsp",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-12-31"
        }])
        
        result = IngredientParser.parse(response)
        
        assert result[0]["quantity"] == 0.5
    
    def test_parse_confidence_out_of_range_uses_default(self):
        """Test that out-of-range confidence values use default."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25",
            "confidence": 1.5
        }])
        
        result = IngredientParser.parse(response)
        
        # Should be clamped to valid range or use default
        assert 0.0 <= result[0]["confidence"] <= 1.0
    
    def test_parse_with_special_characters_in_name(self):
        """Test parsing ingredient names with special characters."""
        response = json.dumps([{
            "name": "bell pepper (red)",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        
        assert "bell pepper" in result[0]["name"]


class TestIngredientParserPrettyPrint:
    """Tests for IngredientParser.pretty_print() method."""
    
    def test_pretty_print_single_ingredient(self):
        """Test pretty-printing a single ingredient."""
        ingredients = [{
            "name": "tomato",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25",
            "confidence": 0.95
        }]
        
        result = IngredientParser.pretty_print(ingredients)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "tomato"
    
    def test_pretty_print_multiple_ingredients(self):
        """Test pretty-printing multiple ingredients."""
        ingredients = [
            {
                "name": "tomato",
                "quantity": 2.0,
                "unit": "pcs",
                "acquisition_date": "2024-01-15",
                "expiration_date": "2024-01-25",
                "confidence": 0.95
            },
            {
                "name": "lettuce",
                "quantity": 1.0,
                "unit": "head",
                "acquisition_date": "2024-01-16",
                "expiration_date": "2024-01-22",
                "confidence": 0.92
            }
        ]
        
        result = IngredientParser.pretty_print(ingredients)
        
        parsed = json.loads(result)
        assert len(parsed) == 2
    
    def test_pretty_print_empty_list(self):
        """Test pretty-printing empty ingredient list."""
        ingredients = []
        
        result = IngredientParser.pretty_print(ingredients)
        
        parsed = json.loads(result)
        assert parsed == []
    
    def test_pretty_print_produces_valid_json(self):
        """Test that output is valid JSON."""
        ingredients = [{
            "name": "tomato",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }]
        
        result = IngredientParser.pretty_print(ingredients)
        
        # Should not raise
        json.loads(result)
    
    def test_pretty_print_includes_required_fields(self):
        """Test that all required fields are in output."""
        ingredients = [{
            "name": "tomato",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }]
        
        result = IngredientParser.pretty_print(ingredients)
        parsed = json.loads(result)
        
        item = parsed[0]
        assert "name" in item
        assert "quantity" in item
        assert "unit" in item
        assert "acquisition_date" in item
        assert "expiration_date" in item
        assert "confidence" in item


class TestIngredientParserRoundTrip:
    """Tests for round-trip consistency: parse → pretty_print → parse."""
    
    def test_round_trip_single_ingredient(self):
        """Test round-trip consistency with single ingredient."""
        original_json = json.dumps([{
            "name": "tomato",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25",
            "confidence": 0.95
        }])
        
        # Parse
        parsed_1 = IngredientParser.parse(original_json)
        
        # Pretty-print
        serialized = IngredientParser.pretty_print(parsed_1)
        
        # Parse again
        parsed_2 = IngredientParser.parse(serialized)
        
        # Should be equivalent
        assert len(parsed_1) == len(parsed_2)
        assert parsed_1[0]["name"] == parsed_2[0]["name"]
        assert parsed_1[0]["quantity"] == parsed_2[0]["quantity"]
        assert parsed_1[0]["unit"] == parsed_2[0]["unit"]
        assert parsed_1[0]["acquisition_date"] == parsed_2[0]["acquisition_date"]
        assert parsed_1[0]["expiration_date"] == parsed_2[0]["expiration_date"]
    
    def test_round_trip_multiple_ingredients(self):
        """Test round-trip with multiple ingredients."""
        original_json = json.dumps([
            {
                "name": "tomato",
                "quantity": 2.0,
                "unit": "pcs",
                "acquisition_date": "2024-01-15",
                "expiration_date": "2024-01-25"
            },
            {
                "name": "lettuce",
                "quantity": 1.0,
                "unit": "head",
                "acquisition_date": "2024-01-16",
                "expiration_date": "2024-01-22"
            }
        ])
        
        parsed_1 = IngredientParser.parse(original_json)
        serialized = IngredientParser.pretty_print(parsed_1)
        parsed_2 = IngredientParser.parse(serialized)
        
        assert len(parsed_1) == len(parsed_2)
        for ing1, ing2 in zip(parsed_1, parsed_2):
            assert ing1["name"] == ing2["name"]
            assert ing1["quantity"] == ing2["quantity"]
            assert ing1["unit"] == ing2["unit"]
    
    def test_round_trip_empty_list(self):
        """Test round-trip with empty ingredient list."""
        original_json = json.dumps([])
        
        parsed_1 = IngredientParser.parse(original_json)
        serialized = IngredientParser.pretty_print(parsed_1)
        parsed_2 = IngredientParser.parse(serialized)
        
        assert parsed_1 == []
        assert parsed_2 == []
    
    def test_round_trip_property_test(self):
        """Test the dedicated round_trip_test method."""
        test_json = json.dumps([{
            "name": "tomato",
            "quantity": 2.5,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25",
            "confidence": 0.9
        }])
        
        result = IngredientParser.round_trip_test(test_json)
        
        assert result is True
    
    def test_round_trip_with_various_units(self):
        """Test round-trip with various unit types."""
        units = ["pcs", "kg", "g", "ml", "cup", "tbsp", "tsp"]
        
        for unit in units:
            original_json = json.dumps([{
                "name": "ingredient",
                "quantity": 1.0,
                "unit": unit,
                "acquisition_date": "2024-01-15",
                "expiration_date": "2024-01-25"
            }])
            
            parsed_1 = IngredientParser.parse(original_json)
            serialized = IngredientParser.pretty_print(parsed_1)
            parsed_2 = IngredientParser.parse(serialized)
            
            assert parsed_1[0]["unit"] == parsed_2[0]["unit"]


class TestIngredientParserErrorHandling:
    """Tests for error handling and edge cases."""
    
    def test_empty_ingredient_name_is_skipped(self):
        """Test that empty ingredient name is skipped gracefully."""
        response = json.dumps([{
            "name": "",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        assert result == []
    
    def test_whitespace_only_name_is_skipped(self):
        """Test that whitespace-only name is skipped gracefully."""
        response = json.dumps([{
            "name": "   ",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        assert result == []
    
    def test_non_dict_item_in_list_is_skipped(self):
        """Test that non-dict items in list are skipped gracefully."""
        response = json.dumps([
            "not a dict"
        ])
        
        result = IngredientParser.parse(response)
        assert result == []
    
    def test_quantity_as_string_is_converted(self):
        """Test that string quantity is converted to float."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": "2.5",
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        
        assert result[0]["quantity"] == 2.5
    
    def test_invalid_quantity_string_is_skipped(self):
        """Test that invalid quantity string is skipped gracefully."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": "not a number",
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        assert result == []
    
    def test_mixed_valid_and_invalid_items(self):
        """Test that valid items are parsed and invalid ones skipped."""
        response = json.dumps([
            {
                "name": "tomato",
                "quantity": 2.0,
                "unit": "pcs",
                "acquisition_date": "2024-01-15",
                "expiration_date": "2024-01-25"
            },
            {
                "name": "",  # Invalid - empty name
                "quantity": 1.0,
                "unit": "head",
                "acquisition_date": "2024-01-16",
                "expiration_date": "2024-01-22"
            },
            {
                "name": "lettuce",
                "quantity": 1.0,
                "unit": "head",
                "acquisition_date": "2024-01-16",
                "expiration_date": "2024-01-22"
            }
        ])
        
        result = IngredientParser.parse(response)
        
        # Should have parsed only 2 valid items
        assert len(result) == 2
        assert result[0]["name"] == "tomato"
        assert result[1]["name"] == "lettuce"
    
    def test_expiration_before_acquisition_warning(self):
        """Test that expiration before acquisition generates warning but processes item."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-25",
            "expiration_date": "2024-01-15"
        }])
        
        # Should still parse but log warning
        result = IngredientParser.parse(response)
        
        assert len(result) == 1


class TestIngredientParserFieldExtraction:
    """Tests for correct field extraction - Property 12: Vision Parser Field Extraction."""
    
    def test_extract_ingredient_name(self):
        """Test extracting ingredient name field."""
        response = json.dumps([{
            "name": "bell pepper",
            "quantity": 1.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        
        assert "name" in result[0]
        assert isinstance(result[0]["name"], str)
    
    def test_extract_quantity_field(self):
        """Test extracting quantity field."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": 2.5,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        
        assert "quantity" in result[0]
        assert isinstance(result[0]["quantity"], float)
    
    def test_extract_unit_field(self):
        """Test extracting unit field."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": 500.0,
            "unit": "g",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        
        assert "unit" in result[0]
        assert isinstance(result[0]["unit"], str)
    
    def test_extract_date_fields(self):
        """Test extracting date fields."""
        response = json.dumps([{
            "name": "tomato",
            "quantity": 2.0,
            "unit": "pcs",
            "acquisition_date": "2024-01-15",
            "expiration_date": "2024-01-25"
        }])
        
        result = IngredientParser.parse(response)
        
        assert "acquisition_date" in result[0]
        assert "expiration_date" in result[0]
        assert result[0]["acquisition_date"] == "2024-01-15"
        assert result[0]["expiration_date"] == "2024-01-25"
