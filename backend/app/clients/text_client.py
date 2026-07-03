"""
Claude Text API client for recipe generation and ingredient substitution suggestions.

This module provides the ClaudeTextClient class which interfaces with Claude Sonnet 4
Text API to generate recipe recommendations and substitution suggestions based on
available ingredients.

Requirements Satisfied:
- 10.1: Authenticate with Claude API using secure credentials
- 10.3: Use Text API for recipe and substitution generation
- 10.6: Implement retry logic with up to 2 additional retries
"""

import json
import os
import re
from typing import List, Dict, Any, Optional
from datetime import date

from openai import OpenAI

from app.clients.ai_config import get_base_url, get_model, completion_kwargs


class TextAPIError(Exception):
    """Custom exception for Text API failures."""
    
    def __init__(self, message: str, retry_count: int = 0, original_error: Optional[Exception] = None):
        """
        Initialize TextAPIError.
        
        Args:
            message: Error description
            retry_count: Number of retry attempts made before failure
            original_error: The underlying exception if applicable
        """
        self.message = message
        self.retry_count = retry_count
        self.original_error = original_error
        super().__init__(f"{message} (retries: {retry_count})")


class ClaudeTextClient:
    """
    Client for Claude Sonnet 4 Text API.
    
    Handles recipe generation and ingredient substitution suggestions with
    built-in retry logic and structured prompt engineering.
    
    Validates: Requirements 10.1, 10.3, 10.6
    """
    
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 2):
        """
        Initialize the Claude Text API client.
        
        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY environment variable.
            max_retries: Maximum number of retry attempts for API failures (default: 2).
                        Total attempts = 1 + max_retries (initial + retries).
        
        Raises:
            ValueError: If API key is not provided and environment variable not set.
        
        Validates: Requirement 10.1 (API key configuration)
        """
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not provided. Pass api_key argument or set "
                "OPENAI_API_KEY environment variable."
            )
        
        self.api_key = api_key
        self.max_retries = max_retries
        self.client = OpenAI(api_key=api_key, base_url=get_base_url())
        self.model = get_model()
    
    def _parse_json_response(self, text: str) -> Dict[str, Any] | List[Dict[str, Any]]:
        """
        Parse JSON from Claude's response, handling markdown fences.
        
        Args:
            text: Raw response text from Claude API
            
        Returns:
            Parsed JSON object or array
            
        Raises:
            ValueError: If JSON parsing fails
        """
        try:
            # Remove markdown code fences if present
            cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}\nRaw text: {text[:200]}")
    
    async def generate_recipes(
        self,
        ingredients: List[str],
        expiring_items: Optional[List[str]] = None,
        max_recipes: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate recipe recommendations from available ingredients.
        
        This method constructs a structured prompt that prioritizes recipes using
        expiring items and sends it to Claude Text API for processing.
        
        Args:
            ingredients: List of available ingredient names.
            expiring_items: List of ingredients expiring within 3 days (optional).
                           If provided, recipes using these will be prioritized.
            max_recipes: Maximum number of recipes to generate (default: 5).
        
        Returns:
            List of recipe dictionaries with structure:
            {
                "id": "unique-recipe-id",
                "name": "Recipe Name",
                "ingredients": [
                    {"name": "ingredient", "quantity": 2, "unit": "pcs", "available": true}
                ],
                "steps": ["Step 1", "Step 2", ...],
                "prep_time_minutes": 30,
                "match_percentage": 85.0,
                "uses_expiring_items": true,
                "missing_ingredients": ["cream"]
            }
        
        Raises:
            TextAPIError: If all retry attempts fail.
        
        Validates: Requirements 10.3 (Text API for recipes), 10.6 (retry logic)
        """
        expiring_items = expiring_items or []
        
        # Build context-aware prompt
        prompt = self._build_recipe_prompt(
            ingredients=ingredients,
            expiring_items=expiring_items,
            max_recipes=max_recipes,
        )
        
        # Attempt API call with retries
        last_error = None
        for attempt in range(1 + self.max_retries):
            try:
                message = self.client.chat.completions.create(
                    model=self.model,
                    max_completion_tokens=8192,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    **completion_kwargs(),
                )
                
                raw_response = message.choices[0].message.content
                result = self._parse_json_response(raw_response)
                
                # Ensure result is a list
                if isinstance(result, list):
                    return result
                else:
                    # Single recipe returned as dict, wrap in list
                    return [result] if result else []
                    
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    # Retry available, continue loop
                    continue
                else:
                    # No more retries, raise error
                    raise TextAPIError(
                        message=f"Failed to generate recipes after {1 + self.max_retries} attempts",
                        retry_count=self.max_retries,
                        original_error=last_error,
                    )
        
        # Fallback (should not reach here due to exception in loop)
        raise TextAPIError(
            message="Unexpected error in generate_recipes",
            retry_count=self.max_retries,
            original_error=last_error,
        )
    
    async def generate_substitutions(
        self,
        missing_ingredient: str,
        recipe_context: str,
        available_ingredients: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Generate ingredient substitution suggestions.
        
        This method constructs a context-aware prompt that provides recipe context
        and available ingredients to suggest suitable substitutes.
        
        Args:
            missing_ingredient: Name of the ingredient that needs substitution.
            recipe_context: Name or description of the recipe requiring substitution.
            available_ingredients: List of ingredients available in the pantry.
        
        Returns:
            List of substitution suggestions with structure:
            {
                "ingredient": "substitute name",
                "ratio": "substitution ratio (e.g., '1:1')",
                "notes": "preparation notes",
                "available": true/false (whether in pantry)
            }
        
        Raises:
            TextAPIError: If all retry attempts fail.
        
        Validates: Requirements 10.3 (Text API for substitutions), 10.6 (retry logic)
        """
        # Build context-aware prompt
        prompt = self._build_substitution_prompt(
            missing_ingredient=missing_ingredient,
            recipe_context=recipe_context,
            available_ingredients=available_ingredients,
        )
        
        # Attempt API call with retries
        last_error = None
        for attempt in range(1 + self.max_retries):
            try:
                message = self.client.chat.completions.create(
                    model=self.model,
                    max_completion_tokens=2048,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    **completion_kwargs(),
                )
                
                raw_response = message.choices[0].message.content
                result = self._parse_json_response(raw_response)
                
                # Ensure result is a list
                if isinstance(result, list):
                    return result
                else:
                    # Single substitution returned as dict, wrap in list
                    return [result] if result else []
                    
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    # Retry available, continue loop
                    continue
                else:
                    # No more retries, raise error
                    raise TextAPIError(
                        message=f"Failed to generate substitutions after {1 + self.max_retries} attempts",
                        retry_count=self.max_retries,
                        original_error=last_error,
                    )
        
        # Fallback (should not reach here due to exception in loop)
        raise TextAPIError(
            message="Unexpected error in generate_substitutions",
            retry_count=self.max_retries,
            original_error=last_error,
        )
    
    def _build_recipe_prompt(
        self,
        ingredients: List[str],
        expiring_items: List[str],
        max_recipes: int,
    ) -> str:
        """
        Build a structured prompt for recipe generation.
        
        Args:
            ingredients: List of available ingredients.
            expiring_items: List of ingredients expiring soon (for prioritization).
            max_recipes: Number of recipes to generate.
        
        Returns:
            Formatted prompt string.
        
        Validates: Requirement 10.3 (structured prompt building)
        """
        ingredients_str = ", ".join(ingredients) if ingredients else "none"
        expiring_str = ", ".join(expiring_items) if expiring_items else "none"
        
        priority_instruction = ""
        if expiring_items:
            priority_instruction = (
                f"\n\nPRIORITY INSTRUCTION: Prioritize recipes that use these expiring items: {expiring_str}. "
                "These ingredients should be used in at least 1-2 recipes to prevent waste."
            )
        
        prompt = f"""You are RasOI, an AI kitchen assistant. Generate {max_recipes} meal recipes based on available ingredients.

AVAILABLE INGREDIENTS:
{ingredients_str}

EXPIRING INGREDIENTS (if any):
{expiring_str}{priority_instruction}

INSTRUCTIONS:
1. Generate recipes that maximize use of available ingredients
2. For each recipe, calculate matchPercentage as (available_ingredients / total_required) × 100
3. Mark usesExpiringItems as true if the recipe uses any expiring ingredient
4. List missing ingredients that are NOT in the available list
5. Provide 4-7 clear, actionable cooking steps

REQUIRED OUTPUT FORMAT:
Return ONLY a valid JSON array (no markdown fences, no explanation). Each recipe must have this exact structure:
[
  {{
    "id": "unique-recipe-id-string",
    "name": "Recipe Name",
    "ingredients": [
      {{"name": "ingredient_name", "quantity": 2, "unit": "pcs", "available": true}},
      {{"name": "missing_item", "quantity": 1, "unit": "cup", "available": false}}
    ],
    "steps": [
      "Step 1: detailed instruction",
      "Step 2: detailed instruction"
    ],
    "prep_time_minutes": 30,
    "match_percentage": 85.0,
    "uses_expiring_items": true,
    "missing_ingredients": ["item1", "item2"]
  }}
]

CONSTRAINTS:
- Each recipe must have at least 3 ingredients
- match_percentage must be a number between 0 and 100
- steps array must have 4-7 elements
- Sort recipes by match_percentage (highest first)"""
        
        return prompt
    
    def _build_substitution_prompt(
        self,
        missing_ingredient: str,
        recipe_context: str,
        available_ingredients: List[str],
    ) -> str:
        """
        Build a context-aware prompt for substitution suggestions.
        
        Args:
            missing_ingredient: The ingredient needing substitution.
            recipe_context: Recipe name/context.
            available_ingredients: Pantry ingredients available for substitution.
        
        Returns:
            Formatted prompt string.
        
        Validates: Requirement 10.3 (context-aware prompt building)
        """
        available_str = ", ".join(available_ingredients) if available_ingredients else "no other ingredients"
        
        prompt = f"""You are a culinary AI assistant. Suggest ingredient substitutes for a missing ingredient in a recipe.

RECIPE: {recipe_context}
MISSING INGREDIENT: {missing_ingredient}
AVAILABLE PANTRY ITEMS: {available_str}

INSTRUCTIONS:
1. Suggest 1-3 substitutes that work best in this recipe
2. Prioritize substitutes available in the pantry (available: true)
3. If no perfect substitutes in pantry, suggest 1-2 common alternatives (available: false)
4. For each substitute, provide the substitution ratio (e.g., "1:1", "1.5:1")
5. Include brief preparation notes (e.g., "Use 1.5x amount to compensate for milder flavor")

REQUIRED OUTPUT FORMAT:
Return ONLY a valid JSON array (no markdown fences, no explanation):
[
  {{
    "ingredient": "substitute ingredient name",
    "ratio": "ratio string (e.g., '1:1' or '1.5:1')",
    "notes": "brief preparation instructions",
    "available": true
  }},
  {{
    "ingredient": "alternative if not in pantry",
    "ratio": "ratio string",
    "notes": "preparation notes",
    "available": false
  }}
]

CONSTRAINTS:
- Suggest 1-3 alternatives
- Ratios must be clear strings like "1:1", "2:1", "0.75:1"
- Notes should be practical and brief
- available field must match whether substitute is in the provided pantry list"""
        
        return prompt
