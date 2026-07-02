"""
Ingredient Parser — Parse Vision API responses into structured Ingredient objects.

Handles JSON parsing, validation, and serialization of ingredient data
extracted from Claude Vision API with round-trip consistency.

Validates: Requirements 1.6, 12.1, 12.2, 12.4, 12.5
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import date

logger = logging.getLogger(__name__)


class IngredientParseError(Exception):
    """Raised when ingredient parsing fails."""
    pass


class IngredientParser:
    """
    Parser for ingredient data from Vision API responses.
    
    Handles conversion between Claude Vision API JSON format and structured
    Ingredient dictionaries with validation and round-trip consistency.
    """
    
    # Expected fields in Vision API response
    REQUIRED_FIELDS = {"name", "quantity", "unit", "acquisition_date", "expiration_date"}
    OPTIONAL_FIELDS = {"confidence"}
    ALL_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS
    
    @staticmethod
    def parse(response_text: str) -> List[Dict[str, Any]]:
        """
        Parse Vision API JSON response into structured Ingredient list.
        
        Args:
            response_text: Raw JSON string from Claude Vision API
        
        Returns:
            List of dictionaries with validated ingredient data:
            - name (str): Ingredient name
            - quantity (float): Numeric amount
            - unit (str): Unit of measurement
            - acquisition_date (str): ISO 8601 date
            - expiration_date (str): ISO 8601 date
            - confidence (float): Confidence 0-1 (optional)
        
        Raises:
            IngredientParseError: If JSON is malformed or fields invalid
        
        Validates: Requirements 12.1, 12.2, 12.4, 12.5
        """
        try:
            # Parse JSON
            raw_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in Vision response: {str(e)}"
            logger.error(f"[ingredient_parser] {error_msg}")
            raise IngredientParseError(error_msg)
        
        # Ensure response is a list
        if not isinstance(raw_data, list):
            error_msg = "Vision API response must be a JSON array, not a single object"
            logger.error(f"[ingredient_parser] {error_msg}")
            raise IngredientParseError(error_msg)
        
        if len(raw_data) == 0:
            logger.info("[ingredient_parser] Empty ingredient list from Vision API")
            return []
        
        # Parse each ingredient
        ingredients = []
        for idx, item in enumerate(raw_data):
            try:
                ingredient = IngredientParser._validate_ingredient(item, idx)
                ingredients.append(ingredient)
            except IngredientParseError as e:
                logger.warning(f"[ingredient_parser] Skipping ingredient {idx}: {str(e)}")
                continue
        
        logger.info(
            f"[ingredient_parser] Successfully parsed {len(ingredients)}/{len(raw_data)} ingredients"
        )
        
        return ingredients
    
    @staticmethod
    def _validate_ingredient(item: Any, idx: int) -> Dict[str, Any]:
        """
        Validate and normalize a single ingredient item.
        
        Args:
            item: Raw ingredient dict from Vision API
            idx: Index in the list (for error reporting)
        
        Returns:
            Validated ingredient dictionary
        
        Raises:
            IngredientParseError: If validation fails
        """
        if not isinstance(item, dict):
            raise IngredientParseError(f"Item {idx} is not a dictionary: {type(item)}")
        
        # Check required fields
        missing_fields = IngredientParser.REQUIRED_FIELDS - set(item.keys())
        if missing_fields:
            raise IngredientParseError(
                f"Item {idx} missing required fields: {missing_fields}"
            )
        
        # Validate and normalize each field
        try:
            name = str(item.get("name", "")).strip()
            if not name:
                raise IngredientParseError(f"Item {idx} has empty name")
            
            quantity = float(item.get("quantity", 1))
            if quantity < 0:
                raise IngredientParseError(f"Item {idx} quantity cannot be negative: {quantity}")
            
            unit = str(item.get("unit", "pcs")).strip()
            if not unit:
                raise IngredientParseError(f"Item {idx} has empty unit")
            
            # Validate dates
            acq_date_str = str(item.get("acquisition_date", "")).strip()
            try:
                acq_date = date.fromisoformat(acq_date_str)
            except ValueError:
                raise IngredientParseError(
                    f"Item {idx} acquisition_date invalid format: {acq_date_str}"
                )
            
            exp_date_str = str(item.get("expiration_date", "")).strip()
            try:
                exp_date = date.fromisoformat(exp_date_str)
            except ValueError:
                raise IngredientParseError(
                    f"Item {idx} expiration_date invalid format: {exp_date_str}"
                )
            
            # Validate expiration is after acquisition
            if exp_date < acq_date:
                logger.warning(
                    f"[ingredient_parser] Item {idx} ({name}): "
                    f"expiration_date {exp_date_str} before acquisition_date {acq_date_str} "
                    f"— will use as-is"
                )
            
            # Optional confidence field
            confidence = 1.0
            if "confidence" in item:
                try:
                    confidence = float(item.get("confidence", 1.0))
                    if not (0.0 <= confidence <= 1.0):
                        raise ValueError(f"Confidence out of range: {confidence}")
                except (ValueError, TypeError):
                    logger.warning(
                        f"[ingredient_parser] Item {idx} ({name}): "
                        f"invalid confidence {item.get('confidence')}, using 1.0"
                    )
                    confidence = 1.0
            
            return {
                "name": name.lower(),
                "quantity": quantity,
                "unit": unit,
                "acquisition_date": acq_date.isoformat(),
                "expiration_date": exp_date.isoformat(),
                "confidence": confidence,
            }
        
        except IngredientParseError:
            raise
        except Exception as e:
            raise IngredientParseError(f"Item {idx} validation error: {str(e)}")
    
    @staticmethod
    def pretty_print(ingredients: List[Dict[str, Any]]) -> str:
        """
        Serialize ingredients list to JSON string.
        
        Produces Vision API-compatible JSON format with proper formatting.
        
        Args:
            ingredients: List of ingredient dictionaries
        
        Returns:
            Pretty-printed JSON string
        
        Validates: Requirement 12.2 (serialization)
        """
        # Ensure all ingredients have required fields
        validated = []
        for ing in ingredients:
            validated_ing = {
                "name": ing.get("name", "unknown"),
                "quantity": float(ing.get("quantity", 1)),
                "unit": ing.get("unit", "pcs"),
                "acquisition_date": str(ing.get("acquisition_date", "")),
                "expiration_date": str(ing.get("expiration_date", "")),
                "confidence": float(ing.get("confidence", 1.0)),
            }
            validated.append(validated_ing)
        
        return json.dumps(validated, indent=2)
    
    @staticmethod
    def round_trip_test(original_json: str) -> bool:
        """
        Test round-trip consistency: parse → serialize → parse.
        
        Validates: Requirements 1.6, 12.4 (round-trip property)
        
        Args:
            original_json: Original JSON string
        
        Returns:
            True if parse → serialize → parse produces equivalent data
        """
        try:
            # Parse original
            ingredients_1 = IngredientParser.parse(original_json)
            if not ingredients_1:
                return True  # Empty list is consistent
            
            # Serialize
            serialized = IngredientParser.pretty_print(ingredients_1)
            
            # Parse again
            ingredients_2 = IngredientParser.parse(serialized)
            
            # Compare
            if len(ingredients_1) != len(ingredients_2):
                logger.error(
                    "[ingredient_parser] Round-trip: ingredient count mismatch "
                    f"{len(ingredients_1)} != {len(ingredients_2)}"
                )
                return False
            
            for ing1, ing2 in zip(ingredients_1, ingredients_2):
                # Compare all fields (allowing small float differences)
                if ing1["name"] != ing2["name"]:
                    logger.error(
                        f"[ingredient_parser] Round-trip: name mismatch "
                        f"{ing1['name']} != {ing2['name']}"
                    )
                    return False
                
                if abs(ing1["quantity"] - ing2["quantity"]) > 0.0001:
                    logger.error(
                        "[ingredient_parser] Round-trip: quantity mismatch "
                        f"{ing1['quantity']} != {ing2['quantity']}"
                    )
                    return False
                
                if ing1["unit"] != ing2["unit"]:
                    logger.error(
                        f"[ingredient_parser] Round-trip: unit mismatch "
                        f"{ing1['unit']} != {ing2['unit']}"
                    )
                    return False
                
                if ing1["acquisition_date"] != ing2["acquisition_date"]:
                    logger.error(
                        "[ingredient_parser] Round-trip: acquisition_date mismatch"
                    )
                    return False
                
                if ing1["expiration_date"] != ing2["expiration_date"]:
                    logger.error(
                        "[ingredient_parser] Round-trip: expiration_date mismatch"
                    )
                    return False
            
            logger.info("[ingredient_parser] Round-trip test PASSED")
            return True
        
        except Exception as e:
            logger.error(f"[ingredient_parser] Round-trip test failed: {str(e)}")
            return False
