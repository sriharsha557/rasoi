"""
Test suite for SubstitutionParser.

Tests validation of substitution data parsing and serialization,
including field validation and round-trip consistency.

Validates: Requirements 5.3, 10.5
"""

import pytest
import json
from app.utils.substitution_parser import (
    SubstitutionParser,
    SubstitutionParseError,
)


class TestSubstitutionParserInitialization:
    """Test parser class initialization and structure."""
    
    def test_required_fields_defined(self):
        """Verify required fields are properly defined."""
        assert SubstitutionParser.REQUIRED_FIELDS == {"ingredient", "ratio", "notes"}
    
    def test_optional_fields_defined(self):
        """Verify optional fields are properly defined."""
        assert SubstitutionParser.OPTIONAL_FIELDS == {"available"}


class TestSubstitutionParserParse:
    """Test parsing of Text API substitution responses."""
    
    def test_parse_single_substitution(self):
        """Test parsing a single substitution from JSON."""
        json_data = json.dumps([
            {
                "ingredient": "Greek yogurt",
                "ratio": "1:1",
                "notes": "Works great in sauces",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        
        assert len(result) == 1
        assert result[0]["ingredient"] == "Greek yogurt"
        assert result[0]["ratio"] == "1:1"
        assert result[0]["notes"] == "Works great in sauces"
        assert result[0]["available"] is True
    
    def test_parse_multiple_substitutions(self):
        """Test parsing multiple substitutions."""
        json_data = json.dumps([
            {
                "ingredient": "Butter",
                "ratio": "1:1",
                "notes": "Neutral flavor",
                "available": True,
            },
            {
                "ingredient": "Coconut oil",
                "ratio": "3:4",
                "notes": "Slight flavor difference",
                "available": False,
            },
            {
                "ingredient": "Applesauce",
                "ratio": "1:1",
                "notes": "Better for baking",
                "available": True,
            },
        ])
        
        result = SubstitutionParser.parse(json_data)
        
        assert len(result) == 3
        assert result[0]["ingredient"] == "Butter"
        assert result[1]["ingredient"] == "Coconut oil"
        assert result[2]["ingredient"] == "Applesauce"
    
    def test_parse_empty_list(self):
        """Test parsing an empty substitution list."""
        json_data = json.dumps([])
        result = SubstitutionParser.parse(json_data)
        assert result == []
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises SubstitutionParseError."""
        with pytest.raises(SubstitutionParseError) as exc_info:
            SubstitutionParser.parse("{invalid json}")
        assert "Invalid JSON" in str(exc_info.value)
    
    def test_parse_non_array_response(self):
        """Test parsing non-array response raises SubstitutionParseError."""
        json_data = json.dumps({"ingredient": "test", "ratio": "1:1", "notes": "test"})
        with pytest.raises(SubstitutionParseError) as exc_info:
            SubstitutionParser.parse(json_data)
        assert "must be a JSON array" in str(exc_info.value)
    
    def test_parse_missing_required_field_ingredient(self):
        """Test parsing with missing ingredient field."""
        json_data = json.dumps([
            {
                "ratio": "1:1",
                "notes": "Some notes",
                "available": True,
            }
        ])
        
        # Should skip invalid item but not raise
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 0
    
    def test_parse_missing_required_field_ratio(self):
        """Test parsing with missing ratio field."""
        json_data = json.dumps([
            {
                "ingredient": "Butter",
                "notes": "Some notes",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 0
    
    def test_parse_missing_required_field_notes(self):
        """Test parsing with missing notes field."""
        json_data = json.dumps([
            {
                "ingredient": "Butter",
                "ratio": "1:1",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 0
    
    def test_parse_empty_ingredient_name(self):
        """Test parsing with empty ingredient name."""
        json_data = json.dumps([
            {
                "ingredient": "",
                "ratio": "1:1",
                "notes": "Some notes",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 0
    
    def test_parse_empty_ratio(self):
        """Test parsing with empty ratio."""
        json_data = json.dumps([
            {
                "ingredient": "Butter",
                "ratio": "",
                "notes": "Some notes",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 0
    
    def test_parse_empty_notes(self):
        """Test parsing with empty notes."""
        json_data = json.dumps([
            {
                "ingredient": "Butter",
                "ratio": "1:1",
                "notes": "",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 0
    
    def test_parse_non_dict_item(self):
        """Test parsing with non-dict item in list."""
        json_data = json.dumps([
            "not a dict",
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 0
    
    def test_parse_missing_optional_available_field(self):
        """Test parsing without optional 'available' field."""
        json_data = json.dumps([
            {
                "ingredient": "Butter",
                "ratio": "1:1",
                "notes": "Works well",
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 1
        assert result[0]["available"] is False  # Default is False
    
    def test_parse_whitespace_trimming(self):
        """Test that whitespace is trimmed from fields."""
        json_data = json.dumps([
            {
                "ingredient": "  Butter  ",
                "ratio": "  1:1  ",
                "notes": "  Works well  ",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert result[0]["ingredient"] == "Butter"
        assert result[0]["ratio"] == "1:1"
        assert result[0]["notes"] == "Works well"
    
    def test_parse_special_characters_in_ingredient(self):
        """Test parsing with special characters."""
        json_data = json.dumps([
            {
                "ingredient": "Greek yogurt (plain, unsweetened)",
                "ratio": "1:1",
                "notes": "Works great in sauces & dips",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert result[0]["ingredient"] == "Greek yogurt (plain, unsweetened)"
        assert result[0]["notes"] == "Works great in sauces & dips"
    
    def test_parse_skip_invalid_among_valid(self):
        """Test that parser skips invalid items but keeps valid ones."""
        json_data = json.dumps([
            {
                "ingredient": "Butter",
                "ratio": "1:1",
                "notes": "Valid",
                "available": True,
            },
            {
                "ingredient": "",
                "ratio": "1:1",
                "notes": "Invalid - empty ingredient",
                "available": True,
            },
            {
                "ingredient": "Oil",
                "ratio": "1:1",
                "notes": "Valid",
                "available": False,
            },
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 2
        assert result[0]["ingredient"] == "Butter"
        assert result[1]["ingredient"] == "Oil"


class TestSubstitutionParserPrettyPrint:
    """Test serialization of substitutions to JSON."""
    
    def test_pretty_print_single_substitution(self):
        """Test serializing a single substitution."""
        substitutions = [
            {
                "ingredient": "Butter",
                "ratio": "1:1",
                "notes": "Works well",
                "available": True,
            }
        ]
        
        result = SubstitutionParser.pretty_print(substitutions)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["ingredient"] == "Butter"
        assert parsed[0]["ratio"] == "1:1"
        assert parsed[0]["notes"] == "Works well"
        assert parsed[0]["available"] is True
    
    def test_pretty_print_multiple_substitutions(self):
        """Test serializing multiple substitutions."""
        substitutions = [
            {
                "ingredient": "Butter",
                "ratio": "1:1",
                "notes": "Works well",
                "available": True,
            },
            {
                "ingredient": "Oil",
                "ratio": "3:4",
                "notes": "Use less",
                "available": False,
            },
        ]
        
        result = SubstitutionParser.pretty_print(substitutions)
        parsed = json.loads(result)
        
        assert len(parsed) == 2
        assert parsed[0]["ingredient"] == "Butter"
        assert parsed[1]["ingredient"] == "Oil"
    
    def test_pretty_print_empty_list(self):
        """Test serializing empty list."""
        result = SubstitutionParser.pretty_print([])
        parsed = json.loads(result)
        assert parsed == []
    
    def test_pretty_print_with_missing_fields(self):
        """Test that pretty_print handles missing fields with defaults."""
        substitutions = [
            {
                "ingredient": "Butter",
            }
        ]
        
        result = SubstitutionParser.pretty_print(substitutions)
        parsed = json.loads(result)
        
        assert parsed[0]["ingredient"] == "Butter"
        assert parsed[0]["ratio"] == "to taste"
        assert parsed[0]["notes"] == ""
        assert parsed[0]["available"] is False
    
    def test_pretty_print_formatting(self):
        """Test that output is properly formatted JSON."""
        substitutions = [
            {
                "ingredient": "Butter",
                "ratio": "1:1",
                "notes": "Works well",
                "available": True,
            }
        ]
        
        result = SubstitutionParser.pretty_print(substitutions)
        
        # Should have proper indentation
        assert "\n" in result  # Multiple lines
        assert "  " in result  # Indentation


class TestSubstitutionParserRoundTrip:
    """Test round-trip consistency: parse → serialize → parse."""
    
    def test_round_trip_single_substitution(self):
        """Test round-trip with single substitution."""
        original_json = json.dumps([
            {
                "ingredient": "Butter",
                "ratio": "1:1",
                "notes": "Works well",
                "available": True,
            }
        ])
        
        # Parse → serialize → parse
        first_parse = SubstitutionParser.parse(original_json)
        serialized = SubstitutionParser.pretty_print(first_parse)
        second_parse = SubstitutionParser.parse(serialized)
        
        assert len(first_parse) == len(second_parse)
        assert first_parse[0]["ingredient"] == second_parse[0]["ingredient"]
        assert first_parse[0]["ratio"] == second_parse[0]["ratio"]
        assert first_parse[0]["notes"] == second_parse[0]["notes"]
    
    def test_round_trip_multiple_substitutions(self):
        """Test round-trip with multiple substitutions."""
        original_json = json.dumps([
            {
                "ingredient": "Butter",
                "ratio": "1:1",
                "notes": "Works well",
                "available": True,
            },
            {
                "ingredient": "Coconut oil",
                "ratio": "3:4",
                "notes": "Use less",
                "available": False,
            },
            {
                "ingredient": "Applesauce",
                "ratio": "1:1",
                "notes": "Better for baking",
                "available": True,
            },
        ])
        
        first_parse = SubstitutionParser.parse(original_json)
        serialized = SubstitutionParser.pretty_print(first_parse)
        second_parse = SubstitutionParser.parse(serialized)
        
        assert len(first_parse) == len(second_parse) == 3
        for i in range(3):
            assert first_parse[i]["ingredient"] == second_parse[i]["ingredient"]
            assert first_parse[i]["ratio"] == second_parse[i]["ratio"]
            assert first_parse[i]["notes"] == second_parse[i]["notes"]
            assert first_parse[i]["available"] == second_parse[i]["available"]
    
    def test_round_trip_empty_list(self):
        """Test round-trip with empty list."""
        original_json = json.dumps([])
        
        first_parse = SubstitutionParser.parse(original_json)
        serialized = SubstitutionParser.pretty_print(first_parse)
        second_parse = SubstitutionParser.parse(serialized)
        
        assert first_parse == second_parse == []
    
    def test_round_trip_test_method(self):
        """Test the built-in round_trip_test method."""
        json_data = json.dumps([
            {
                "ingredient": "Butter",
                "ratio": "1:1",
                "notes": "Works well",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.round_trip_test(json_data)
        assert result is True
    
    def test_round_trip_test_empty_list(self):
        """Test round_trip_test with empty list."""
        json_data = json.dumps([])
        result = SubstitutionParser.round_trip_test(json_data)
        assert result is True


class TestSubstitutionRatioExtraction:
    """Property 15: Substitution Ratio Extraction.
    
    **Validates: Requirements 5.3**
    
    For any Text AI substitution response containing substitution suggestions,
    the parser SHALL extract ingredient name, substitution ratio string, and
    notes for each suggestion.
    """
    
    @pytest.mark.parametrize(
        "ratio",
        [
            "1:1",
            "2:1",
            "1:2",
            "use 2 tsp per 1 tbsp",
            "80% of original",
            "3/4 cup for 1 cup",
        ],
    )
    def test_ratio_extraction_various_formats(self, ratio):
        """Test extraction of various ratio formats."""
        json_data = json.dumps([
            {
                "ingredient": "Test ingredient",
                "ratio": ratio,
                "notes": "Notes about substitution",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 1
        assert result[0]["ratio"] == ratio
    
    @pytest.mark.parametrize(
        "ingredient",
        [
            "Olive oil",
            "Greek yogurt",
            "Almond milk (unsweetened)",
            "Brown rice flour",
            "Agave nectar",
        ],
    )
    def test_ingredient_extraction_various_names(self, ingredient):
        """Test extraction of various ingredient names."""
        json_data = json.dumps([
            {
                "ingredient": ingredient,
                "ratio": "1:1",
                "notes": "Notes about substitution",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 1
        assert result[0]["ingredient"] == ingredient
    
    @pytest.mark.parametrize(
        "notes",
        [
            "Similar texture and flavor",
            "May need to adjust cooking time",
            "Works best in baked goods",
            "Use less as it's more concentrated",
            "Adds a slight nutty flavor",
        ],
    )
    def test_notes_extraction_various_formats(self, notes):
        """Test extraction of various note formats."""
        json_data = json.dumps([
            {
                "ingredient": "Test ingredient",
                "ratio": "1:1",
                "notes": notes,
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        assert len(result) == 1
        assert result[0]["notes"] == notes
    
    def test_complete_substitution_extraction(self):
        """Test extraction of all fields in a complete substitution."""
        json_data = json.dumps([
            {
                "ingredient": "Olive oil",
                "ratio": "1:1",
                "notes": "Use extra virgin for best flavor",
                "available": True,
            }
        ])
        
        result = SubstitutionParser.parse(json_data)
        sub = result[0]
        
        # Verify all fields extracted
        assert "ingredient" in sub
        assert "ratio" in sub
        assert "notes" in sub
        assert "available" in sub
        
        # Verify types
        assert isinstance(sub["ingredient"], str)
        assert isinstance(sub["ratio"], str)
        assert isinstance(sub["notes"], str)
        assert isinstance(sub["available"], bool)
