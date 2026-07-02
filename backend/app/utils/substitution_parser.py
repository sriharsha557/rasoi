"""
Substitution Parser — Parse Text API responses into Substitution objects.

Handles JSON parsing, validation, and serialization of substitution data
extracted from Claude Text API.

Validates: Requirements 5.3, 10.5
"""

import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SubstitutionParseError(Exception):
    """Raised when substitution parsing fails."""
    pass


class SubstitutionParser:
    """
    Parser for substitution data from Text API responses.
    
    Handles conversion between Claude Text API JSON format and structured
    Substitution dictionaries with validation.
    """
    
    # Expected fields in substitution response
    REQUIRED_FIELDS = {"ingredient", "ratio", "notes"}
    OPTIONAL_FIELDS = {"available"}
    ALL_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS
    
    @staticmethod
    def parse(response_text: str) -> List[Dict[str, Any]]:
        """
        Parse Text API JSON response into structured Substitution list.
        
        Args:
            response_text: Raw JSON string from Claude Text API
        
        Returns:
            List of dictionaries with validated substitution data:
            - ingredient (str): Substitute ingredient name
            - ratio (str): Substitution ratio (e.g., "use 2 tsp per 1 tbsp")
            - notes (str): Explanation of taste/texture differences
            - available (bool): Whether available in pantry
        
        Raises:
            SubstitutionParseError: If JSON is malformed or fields invalid
        
        Validates: Requirements 5.3, 10.5
        """
        try:
            # Parse JSON
            raw_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in substitution response: {str(e)}"
            logger.error(f"[substitution_parser] {error_msg}")
            raise SubstitutionParseError(error_msg)
        
        # Ensure response is a list
        if not isinstance(raw_data, list):
            error_msg = "Substitution response must be a JSON array"
            logger.error(f"[substitution_parser] {error_msg}")
            raise SubstitutionParseError(error_msg)
        
        if len(raw_data) == 0:
            logger.info("[substitution_parser] Empty substitution list")
            return []
        
        # Parse each substitution
        substitutions = []
        for idx, item in enumerate(raw_data):
            try:
                substitution = SubstitutionParser._validate_substitution(item, idx)
                substitutions.append(substitution)
            except SubstitutionParseError as e:
                logger.warning(f"[substitution_parser] Skipping item {idx}: {str(e)}")
                continue
        
        logger.info(
            f"[substitution_parser] Successfully parsed "
            f"{len(substitutions)}/{len(raw_data)} substitutions"
        )
        
        return substitutions
    
    @staticmethod
    def _validate_substitution(item: Any, idx: int) -> Dict[str, Any]:
        """
        Validate and normalize a single substitution item.
        
        Args:
            item: Raw substitution dict from Text API
            idx: Index in the list (for error reporting)
        
        Returns:
            Validated substitution dictionary
        
        Raises:
            SubstitutionParseError: If validation fails
        """
        if not isinstance(item, dict):
            raise SubstitutionParseError(f"Item {idx} is not a dictionary: {type(item)}")
        
        # Check required fields
        missing_fields = SubstitutionParser.REQUIRED_FIELDS - set(item.keys())
        if missing_fields:
            raise SubstitutionParseError(
                f"Item {idx} missing required fields: {missing_fields}"
            )
        
        try:
            # Validate ingredient name
            ingredient = str(item.get("ingredient", "")).strip()
            if not ingredient:
                raise SubstitutionParseError(f"Item {idx} has empty ingredient name")
            
            # Validate ratio
            ratio = str(item.get("ratio", "")).strip()
            if not ratio:
                raise SubstitutionParseError(f"Item {idx} has empty ratio")
            
            # Validate notes
            notes = str(item.get("notes", "")).strip()
            if not notes:
                raise SubstitutionParseError(f"Item {idx} has empty notes")
            
            # Optional availability flag
            available = bool(item.get("available", False))
            
            return {
                "ingredient": ingredient,
                "ratio": ratio,
                "notes": notes,
                "available": available,
            }
        
        except SubstitutionParseError:
            raise
        except Exception as e:
            raise SubstitutionParseError(f"Item {idx} validation error: {str(e)}")
    
    @staticmethod
    def pretty_print(substitutions: List[Dict[str, Any]]) -> str:
        """
        Serialize substitutions list to JSON string.
        
        Produces Text API-compatible JSON format with proper formatting.
        
        Args:
            substitutions: List of substitution dictionaries
        
        Returns:
            Pretty-printed JSON string
        """
        validated = []
        for sub in substitutions:
            validated_sub = {
                "ingredient": sub.get("ingredient", "unknown"),
                "ratio": sub.get("ratio", "to taste"),
                "notes": sub.get("notes", ""),
                "available": bool(sub.get("available", False)),
            }
            validated.append(validated_sub)
        
        return json.dumps(validated, indent=2)
    
    @staticmethod
    def round_trip_test(original_json: str) -> bool:
        """
        Test round-trip consistency: parse → serialize → parse.
        
        Args:
            original_json: Original JSON string
        
        Returns:
            True if parse → serialize → parse produces equivalent data
        """
        try:
            # Parse original
            subs_1 = SubstitutionParser.parse(original_json)
            if not subs_1:
                return True
            
            # Serialize
            serialized = SubstitutionParser.pretty_print(subs_1)
            
            # Parse again
            subs_2 = SubstitutionParser.parse(serialized)
            
            # Compare
            if len(subs_1) != len(subs_2):
                logger.error(
                    "[substitution_parser] Round-trip: count mismatch "
                    f"{len(subs_1)} != {len(subs_2)}"
                )
                return False
            
            for s1, s2 in zip(subs_1, subs_2):
                if s1["ingredient"] != s2["ingredient"]:
                    logger.error("[substitution_parser] Round-trip: ingredient mismatch")
                    return False
                
                if s1["ratio"] != s2["ratio"]:
                    logger.error("[substitution_parser] Round-trip: ratio mismatch")
                    return False
                
                if s1["notes"] != s2["notes"]:
                    logger.error("[substitution_parser] Round-trip: notes mismatch")
                    return False
            
            logger.info("[substitution_parser] Round-trip test PASSED")
            return True
        
        except Exception as e:
            logger.error(f"[substitution_parser] Round-trip test failed: {str(e)}")
            return False
