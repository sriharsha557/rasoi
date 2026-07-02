"""
Substitution Service — Ingredient substitution suggestions.

Provides intelligent substitution recommendations for missing ingredients
using Claude Text API with context-aware prompting.

Async-first implementation with proper error handling and logging.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
"""

from typing import List, Dict, Any, Optional
from app.clients import claude_client
from app.database import PantryRepository
import logging

logger = logging.getLogger(__name__)


class SubstitutionService:
    """
    Service for generating ingredient substitution suggestions.
    
    Uses Claude Text API to suggest alternatives for missing ingredients
    based on available pantry items and recipe context.
    Implements async-first patterns throughout.
    """
    
    def __init__(self, repository: PantryRepository):
        """
        Initialize substitution service.
        
        Args:
            repository: PantryRepository instance for pantry lookups
        """
        self.repository = repository
        logger.debug("[substitution_service] Initialized with repository")
    
    async def get_substitutions(
        self,
        missing_ingredient: str,
        recipe_context: str,
        pantry_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Get substitution suggestions for a missing ingredient.
        
        Queries Claude Text API to suggest alternatives based on the recipe
        context and available pantry items. Flags which suggestions are
        available in the user's pantry.
        
        Args:
            missing_ingredient: Name of the missing ingredient
            recipe_context: Name/description of recipe for context
            pantry_items: Optional list of available items. If not provided,
                         fetches from repository.
        
        Returns:
            Dictionary with:
            - success (bool): Whether substitutions were found
            - substitutions (List[Dict]): List of suggestions with fields:
                - ingredient (str): Substitute ingredient name
                - ratio (str): Substitution ratio (e.g., "use 2 tsp")
                - notes (str): Explanation of taste/texture impact
                - available (bool): Whether available in user's pantry
            - message (str): Result message
        
        Validates: Requirements 5.1, 5.2, 5.3, 5.5
        """
        logger.info(
            "[substitution_service] Looking for substitutes for '%s' in recipe '%s'",
            missing_ingredient,
            recipe_context
        )
        
        try:
            # Fetch pantry items if not provided
            if pantry_items is None:
                pantry_items = await self.repository.get_all()
            
            if not pantry_items:
                logger.warning("[substitution_service] Pantry is empty, no substitutes available")
                return {
                    "success": False,
                    "substitutions": [],
                    "message": "Your pantry is empty. No substitutes available.",
                }
            
            # Get available ingredient names
            available_names = [item.get("name", "") for item in pantry_items]
            
            # Get substitution suggestions from Claude
            raw_substitutions = await claude_client.get_substitutions(
                missing_ingredient=missing_ingredient,
                recipe_name=recipe_context,
                pantry_items=pantry_items,
            )
            
            if not raw_substitutions:
                logger.info(
                    "[substitution_service] No substitutes found for '%s'",
                    missing_ingredient
                )
                return {
                    "success": False,
                    "substitutions": [],
                    "message": f"No suitable substitutes found for {missing_ingredient}.",
                }
            
            logger.info(
                "[substitution_service] Claude suggested %d substitutes",
                len(raw_substitutions)
            )
            
            # Enrich substitutions with availability flags
            enriched_substitutions = self._enrich_substitutions(
                raw_substitutions,
                available_names
            )
            
            return {
                "success": True,
                "substitutions": enriched_substitutions,
                "message": f"Found {len(enriched_substitutions)} substitute(s) for {missing_ingredient}.",
            }
        
        except Exception as e:
            logger.error(
                "[substitution_service] Error getting substitutions: %s",
                str(e)
            )
            return {
                "success": False,
                "substitutions": [],
                "message": f"Failed to find substitutes: {str(e)}",
            }
    
    @staticmethod
    def _enrich_substitutions(
        substitutions: List[Dict[str, Any]],
        available_names: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Enrich substitutions with availability flags.
        
        Checks which suggested substitutes are actually available in the pantry
        and updates the 'available' flag accordingly.
        
        Args:
            substitutions: List of substitution dicts from Claude
            available_names: List of available ingredient names
        
        Returns:
            List of substitutions with updated 'available' flags
        
        Validates: Requirement 5.3
        """
        available_lower = {name.lower().strip() for name in available_names}
        
        enriched = []
        for sub in substitutions:
            ingredient_name = sub.get("ingredient", "").lower().strip()
            
            # Check if this substitute is in the pantry
            is_available = any(
                ingredient_name == aname or ingredient_name in aname or aname in ingredient_name
                for aname in available_lower
            )
            
            enriched_sub = {
                "ingredient": sub.get("ingredient", "unknown"),
                "ratio": sub.get("ratio", "to taste"),
                "notes": sub.get("notes", ""),
                "available": is_available or sub.get("available", False),
            }
            enriched.append(enriched_sub)
        
        return enriched
    
    async def validate_substitution(
        self,
        original_ingredient: str,
        substitute_ingredient: str,
    ) -> Dict[str, Any]:
        """
        Validate whether a proposed substitution is suitable.
        
        Useful for checking if a user's manual substitution choice is reasonable.
        
        Args:
            original_ingredient: Original ingredient needed
            substitute_ingredient: Proposed substitute
        
        Returns:
            Dictionary with:
            - valid (bool): Whether substitution is suitable
            - explanation (str): Reason why or why not
        
        Validates: Requirement 5.4
        """
        logger.info(
            "[substitution_service] Validating substitution: %s → %s",
            original_ingredient,
            substitute_ingredient
        )
        
        # Simple validation rules (in production, could use Claude for more sophisticated checks)
        invalid_pairs = [
            ("sugar", "salt"),
            ("flour", "water"),
            ("oil", "vinegar"),
        ]
        
        original_lower = original_ingredient.lower()
        substitute_lower = substitute_ingredient.lower()
        
        for orig, invalid in invalid_pairs:
            if orig in original_lower and invalid in substitute_lower:
                return {
                    "valid": False,
                    "explanation": f"{substitute_ingredient} is not a suitable replacement for {original_ingredient}.",
                }
        
        # Acceptance criteria: if substitute is different and non-empty, consider it valid
        if substitute_lower and substitute_lower != original_lower:
            return {
                "valid": True,
                "explanation": f"{substitute_ingredient} can work as a substitute for {original_ingredient}.",
            }
        
        return {
            "valid": False,
            "explanation": "Invalid substitution.",
        }
