"""
Recipe Parser — Parse Text API responses into structured Recipe objects.

Handles JSON parsing, validation, and serialization of recipe data
extracted from Claude Text API with round-trip consistency.

Validates: Requirements 4.5, 13.1, 13.2, 13.4, 13.5
"""

import json
import logging
from typing import List, Dict, Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class RecipeParseError(Exception):
    """Raised when recipe parsing fails."""
    pass


class RecipeParser:
    """
    Parser for recipe data from Text API responses.
    
    Handles conversion between Claude Text API JSON format and structured
    Recipe dictionaries with validation and round-trip consistency.
    """
    
    # Expected fields in Text API recipe response
    RECIPE_REQUIRED_FIELDS = {
        "name", "ingredients", "steps", "prepTimeMinutes"
    }
    RECIPE_OPTIONAL_FIELDS = {
        "id", "cuisine", "difficulty", "matchPercentage", "usesExpiringItems",
        "missingIngredients"
    }
    RECIPE_ALL_FIELDS = RECIPE_REQUIRED_FIELDS | RECIPE_OPTIONAL_FIELDS
    
    # Expected fields in ingredient objects
    INGREDIENT_REQUIRED_FIELDS = {"name", "quantity", "unit"}
    INGREDIENT_OPTIONAL_FIELDS = {"available"}
    
    @staticmethod
    def parse(response_text: str) -> List[Dict[str, Any]]:
        """
        Parse Text API JSON response into structured Recipe list.
        
        Args:
            response_text: Raw JSON string from Claude Text API
        
        Returns:
            List of dictionaries with validated recipe data:
            - id (str): Unique recipe ID
            - name (str): Recipe name
            - ingredients (List[Dict]): Ingredients with name, quantity, unit, available
            - steps (List[str]): Cooking steps
            - prepTimeMinutes (int): Preparation time
            - matchPercentage (float): % of ingredients available (0-100)
            - usesExpiringItems (bool): Uses expiring ingredients
            - missingIngredients (List[str]): Unavailable ingredients
            - cuisine (str): Cuisine type (optional)
            - difficulty (str): Difficulty level (optional)
        
        Raises:
            RecipeParseError: If JSON is malformed or fields invalid
        
        Validates: Requirements 13.1, 13.2, 13.5
        """
        try:
            # Parse JSON
            raw_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in Text API response: {str(e)}"
            logger.error(f"[recipe_parser] {error_msg}")
            raise RecipeParseError(error_msg)
        
        # Ensure response is a list
        if not isinstance(raw_data, list):
            error_msg = "Text API response must be a JSON array"
            logger.error(f"[recipe_parser] {error_msg}")
            raise RecipeParseError(error_msg)
        
        if len(raw_data) == 0:
            logger.info("[recipe_parser] Empty recipe list from Text API")
            return []
        
        # Parse each recipe
        recipes = []
        for idx, item in enumerate(raw_data):
            try:
                recipe = RecipeParser._validate_recipe(item, idx)
                recipes.append(recipe)
            except RecipeParseError as e:
                logger.warning(f"[recipe_parser] Skipping recipe {idx}: {str(e)}")
                continue
        
        logger.info(
            f"[recipe_parser] Successfully parsed {len(recipes)}/{len(raw_data)} recipes"
        )
        
        return recipes
    
    @staticmethod
    def _validate_recipe(item: Any, idx: int) -> Dict[str, Any]:
        """
        Validate and normalize a single recipe item.
        
        Args:
            item: Raw recipe dict from Text API
            idx: Index in the list (for error reporting)
        
        Returns:
            Validated recipe dictionary
        
        Raises:
            RecipeParseError: If validation fails
        """
        if not isinstance(item, dict):
            raise RecipeParseError(f"Item {idx} is not a dictionary: {type(item)}")
        
        # Check required fields
        missing_fields = RecipeParser.RECIPE_REQUIRED_FIELDS - set(item.keys())
        if missing_fields:
            raise RecipeParseError(
                f"Recipe {idx} missing required fields: {missing_fields}"
            )
        
        try:
            # Validate name
            name = str(item.get("name", "")).strip()
            if not name:
                raise RecipeParseError(f"Recipe {idx} has empty name")
            
            # Validate ingredients
            ingredients_raw = item.get("ingredients", [])
            if not isinstance(ingredients_raw, list):
                raise RecipeParseError(f"Recipe {idx} ingredients must be a list")
            
            ingredients = []
            for ing_idx, ing in enumerate(ingredients_raw):
                validated_ing = RecipeParser._validate_ingredient(ing, idx, ing_idx)
                ingredients.append(validated_ing)
            
            if not ingredients:
                raise RecipeParseError(f"Recipe {idx} has no ingredients")
            
            # Validate steps
            steps_raw = item.get("steps", [])
            if not isinstance(steps_raw, list):
                raise RecipeParseError(f"Recipe {idx} steps must be a list")
            
            steps = [str(s).strip() for s in steps_raw if str(s).strip()]
            if not steps:
                raise RecipeParseError(f"Recipe {idx} has no steps")
            
            # Validate prep time
            try:
                prep_time = int(item.get("prepTimeMinutes", 30))
                if prep_time < 0:
                    raise ValueError(f"Negative prep time: {prep_time}")
            except (ValueError, TypeError):
                raise RecipeParseError(
                    f"Recipe {idx} prepTimeMinutes invalid: {item.get('prepTimeMinutes')}"
                )
            
            # Optional fields
            recipe_id = str(item.get("id", str(uuid4())))
            match_percentage = 0.0
            if "matchPercentage" in item:
                try:
                    match_percentage = float(item.get("matchPercentage", 0))
                    if not (0 <= match_percentage <= 100):
                        raise ValueError(f"Match percentage out of range: {match_percentage}")
                except (ValueError, TypeError):
                    logger.warning(
                        f"[recipe_parser] Recipe {idx} ({name}): "
                        f"invalid matchPercentage, using 0"
                    )
                    match_percentage = 0.0
            
            uses_expiring = bool(item.get("usesExpiringItems", False))
            missing_ingredients = item.get("missingIngredients", [])
            if not isinstance(missing_ingredients, list):
                missing_ingredients = []
            
            cuisine = str(item.get("cuisine", "")).strip() or "Unknown"
            difficulty = str(item.get("difficulty", "")).strip() or "Medium"
            
            return {
                "id": recipe_id,
                "name": name,
                "ingredients": ingredients,
                "steps": steps,
                "prepTimeMinutes": prep_time,
                "matchPercentage": match_percentage,
                "usesExpiringItems": uses_expiring,
                "missingIngredients": [str(m).strip() for m in missing_ingredients],
                "cuisine": cuisine,
                "difficulty": difficulty,
            }
        
        except RecipeParseError:
            raise
        except Exception as e:
            raise RecipeParseError(f"Recipe {idx} validation error: {str(e)}")
    
    @staticmethod
    def _validate_ingredient(ing: Any, recipe_idx: int, ing_idx: int) -> Dict[str, Any]:
        """
        Validate a recipe ingredient object.
        
        Args:
            ing: Raw ingredient dict
            recipe_idx: Parent recipe index
            ing_idx: Ingredient index within recipe
        
        Returns:
            Validated ingredient dictionary
        
        Raises:
            RecipeParseError: If validation fails
        """
        if not isinstance(ing, dict):
            raise RecipeParseError(
                f"Recipe {recipe_idx} ingredient {ing_idx} is not a dictionary"
            )
        
        missing = RecipeParser.INGREDIENT_REQUIRED_FIELDS - set(ing.keys())
        if missing:
            raise RecipeParseError(
                f"Recipe {recipe_idx} ingredient {ing_idx} missing fields: {missing}"
            )
        
        try:
            name = str(ing.get("name", "")).strip()
            if not name:
                raise RecipeParseError(f"Empty ingredient name in recipe {recipe_idx}")
            
            quantity = float(ing.get("quantity", 1))
            if quantity < 0:
                raise RecipeParseError(f"Negative quantity in recipe {recipe_idx}")
            
            unit = str(ing.get("unit", "")).strip()
            if not unit:
                raise RecipeParseError(f"Empty unit in recipe {recipe_idx}")
            
            available = bool(ing.get("available", False))
            
            return {
                "name": name,
                "quantity": quantity,
                "unit": unit,
                "available": available,
            }
        except RecipeParseError:
            raise
        except Exception as e:
            raise RecipeParseError(
                f"Recipe {recipe_idx} ingredient {ing_idx} error: {str(e)}"
            )
    
    @staticmethod
    def pretty_print(recipes: List[Dict[str, Any]]) -> str:
        """
        Serialize recipes list to JSON string.
        
        Produces Text API-compatible JSON format with proper formatting.
        
        Args:
            recipes: List of recipe dictionaries
        
        Returns:
            Pretty-printed JSON string
        
        Validates: Requirement 13.2 (serialization)
        """
        validated = []
        for recipe in recipes:
            validated_recipe = {
                "id": recipe.get("id", str(uuid4())),
                "name": recipe.get("name", "Unknown Recipe"),
                "ingredients": recipe.get("ingredients", []),
                "steps": recipe.get("steps", []),
                "prepTimeMinutes": int(recipe.get("prepTimeMinutes", 30)),
                "matchPercentage": float(recipe.get("matchPercentage", 0)),
                "usesExpiringItems": bool(recipe.get("usesExpiringItems", False)),
                "missingIngredients": recipe.get("missingIngredients", []),
                "cuisine": recipe.get("cuisine", "Unknown"),
                "difficulty": recipe.get("difficulty", "Medium"),
            }
            validated.append(validated_recipe)
        
        return json.dumps(validated, indent=2)
    
    @staticmethod
    def round_trip_test(original_json: str) -> bool:
        """
        Test round-trip consistency: parse → serialize → parse.
        
        Validates: Requirements 13.4 (round-trip property)
        
        Args:
            original_json: Original JSON string
        
        Returns:
            True if parse → serialize → parse produces equivalent data
        """
        try:
            # Parse original
            recipes_1 = RecipeParser.parse(original_json)
            if not recipes_1:
                return True
            
            # Serialize
            serialized = RecipeParser.pretty_print(recipes_1)
            
            # Parse again
            recipes_2 = RecipeParser.parse(serialized)
            
            # Compare
            if len(recipes_1) != len(recipes_2):
                logger.error(
                    "[recipe_parser] Round-trip: recipe count mismatch "
                    f"{len(recipes_1)} != {len(recipes_2)}"
                )
                return False
            
            for r1, r2 in zip(recipes_1, recipes_2):
                if r1["name"] != r2["name"]:
                    logger.error(f"[recipe_parser] Round-trip: name mismatch")
                    return False
                
                if len(r1["ingredients"]) != len(r2["ingredients"]):
                    logger.error(f"[recipe_parser] Round-trip: ingredient count mismatch")
                    return False
                
                if len(r1["steps"]) != len(r2["steps"]):
                    logger.error(f"[recipe_parser] Round-trip: step count mismatch")
                    return False
                
                if r1["prepTimeMinutes"] != r2["prepTimeMinutes"]:
                    logger.error(f"[recipe_parser] Round-trip: prep time mismatch")
                    return False
            
            logger.info("[recipe_parser] Round-trip test PASSED")
            return True
        
        except Exception as e:
            logger.error(f"[recipe_parser] Round-trip test failed: {str(e)}")
            return False
