"""
Scanner Service — Image processing and ingredient extraction coordination.

Coordinates image validation, Claude Vision API calls, parsing, and enrichment
with expiration date estimation.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
"""

from datetime import date, timedelta
from typing import List, Dict, Any
from app.clients import claude_client
import logging

logger = logging.getLogger(__name__)

# Category-based expiration defaults (in days from acquisition)
# Maps ingredient name patterns to typical shelf life
INGREDIENT_SHELF_LIFE = {
    # Produce
    "tomato": 5,
    "potato": 21,
    "carrot": 30,
    "onion": 30,
    "lettuce": 7,
    "spinach": 5,
    "broccoli": 7,
    "cauliflower": 7,
    "cucumber": 7,
    "pepper": 14,
    "apple": 21,
    "banana": 7,
    "orange": 21,
    "lemon": 21,
    "lime": 21,
    "berries": 5,
    "strawberry": 5,
    "blueberry": 7,
    "grape": 7,
    "peach": 5,
    "watermelon": 14,
    "mango": 7,
    "pineapple": 7,
    
    # Dairy
    "milk": 7,
    "yogurt": 14,
    "cheese": 30,
    "butter": 90,
    "cream": 14,
    "egg": 30,
    
    # Pantry staples
    "rice": 365,
    "pasta": 365,
    "bread": 7,
    "flour": 180,
    "oil": 365,
    "salt": 365,
    "sugar": 365,
    "honey": 730,
    
    # Proteins
    "chicken": 2,
    "beef": 3,
    "fish": 2,
    "shrimp": 2,
    "tofu": 7,
    
    # Condiments
    "ketchup": 180,
    "mustard": 180,
    "mayo": 90,
    "soy sauce": 180,
}

# Default shelf life for unknown items (in days)
DEFAULT_SHELF_LIFE_DAYS = 7


class ScannerService:
    """
    Service for processing ingredient scans and enriching ingredient data.
    """
    
    @staticmethod
    def estimate_expiration(ingredient_name: str, acquisition_date: date = None) -> date:
        """
        Estimate expiration date based on ingredient category.
        
        Uses hardcoded ingredient lookup for hackathon demo. In production,
        could integrate with external nutrition/shelf-life APIs.
        
        Args:
            ingredient_name: Name of the ingredient
            acquisition_date: Date when acquired (defaults to today)
        
        Returns:
            Estimated expiration date as a date object
        
        Validates: Requirement 1.3
        """
        if acquisition_date is None:
            acquisition_date = date.today()
        
        # Normalize ingredient name for lookup
        normalized = ingredient_name.lower().strip()
        
        # Check for exact matches first
        if normalized in INGREDIENT_SHELF_LIFE:
            days = INGREDIENT_SHELF_LIFE[normalized]
        else:
            # Check for partial matches (e.g., "cherry tomato" matches "tomato")
            days = DEFAULT_SHELF_LIFE_DAYS
            for key, shelf_days in INGREDIENT_SHELF_LIFE.items():
                if key in normalized or normalized in key:
                    days = shelf_days
                    break
        
        # Calculate expiration date
        expiration_date = acquisition_date + timedelta(days=days)
        return expiration_date
    
    @staticmethod
    async def scan_image(
        image_bytes: bytes,
        scan_type: str,
        media_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """
        Process image scan and extract ingredients.
        
        Coordinates Vision API call, parsing, and enrichment with expiration estimates.
        
        Args:
            image_bytes: Raw image file bytes
            scan_type: Type of scan ("ingredient" or "receipt")
            media_type: MIME type of the image
        
        Returns:
            Dictionary with:
            - success (bool): Whether scan was successful
            - ingredients (List[Dict]): Extracted and enriched ingredient data
            - message (str): Result message
            - raw_count (int): Number of raw ingredients detected
        
        Raises:
            ValueError: If image is empty or invalid
            RuntimeError: If Claude Vision API fails
        
        Validates: Requirements 1.1, 1.2, 1.4, 1.5
        """
        if not image_bytes:
            return {
                "success": False,
                "ingredients": [],
                "message": "Image is empty",
                "raw_count": 0,
            }
        
        logger.info(
            "[scanner_service] Processing %s scan (%d bytes)",
            scan_type,
            len(image_bytes)
        )
        
        try:
            # Call Claude Vision API
            raw_ingredients = await claude_client.extract_ingredients(
                image_bytes=image_bytes,
                media_type=media_type
            )
            
            if not raw_ingredients:
                return {
                    "success": False,
                    "ingredients": [],
                    "message": "No ingredients detected in the image. Try a clearer photo.",
                    "raw_count": 0,
                }
            
            logger.info(
                "[scanner_service] Claude Vision returned %d ingredients",
                len(raw_ingredients)
            )
            
            # Enrich ingredients with expiration estimates
            enriched = []
            for ingredient in raw_ingredients:
                try:
                    acquisition_date = date.fromisoformat(
                        ingredient.get("acquisition_date", date.today().isoformat())
                    )
                    
                    # Estimate expiration if not provided
                    expiration_date_str = ingredient.get("expiration_date")
                    if expiration_date_str:
                        expiration_date = date.fromisoformat(expiration_date_str)
                    else:
                        expiration_date = ScannerService.estimate_expiration(
                            ingredient.get("name", "unknown"),
                            acquisition_date
                        )
                    
                    enriched_item = {
                        "name": ingredient.get("name", "unknown").lower().strip(),
                        "quantity": float(ingredient.get("quantity", 1)),
                        "unit": ingredient.get("unit", "pcs"),
                        "acquisition_date": acquisition_date.isoformat(),
                        "expiration_date": expiration_date.isoformat(),
                        "confidence": float(ingredient.get("confidence", 1.0)),
                    }
                    enriched.append(enriched_item)
                except (ValueError, TypeError) as e:
                    logger.warning(
                        "[scanner_service] Failed to enrich ingredient %s: %s",
                        ingredient.get("name", "unknown"),
                        str(e)
                    )
                    continue
            
            logger.info(
                "[scanner_service] Enriched %d/%d ingredients with expiration estimates",
                len(enriched),
                len(raw_ingredients)
            )
            
            return {
                "success": True,
                "ingredients": enriched,
                "message": f"Successfully detected {len(enriched)} ingredient(s) from your {scan_type}.",
                "raw_count": len(raw_ingredients),
            }
        
        except RuntimeError as e:
            logger.error("[scanner_service] Claude Vision API error: %s", str(e))
            return {
                "success": False,
                "ingredients": [],
                "message": f"Vision API error: {str(e)}",
                "raw_count": 0,
            }
        except Exception as e:
            logger.error("[scanner_service] Unexpected error during scan: %s", str(e))
            return {
                "success": False,
                "ingredients": [],
                "message": f"Failed to process image: {str(e)}",
                "raw_count": 0,
            }
