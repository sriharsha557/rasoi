"""
Scanner Service — Image processing and ingredient extraction coordination.

Coordinates image validation, Claude Vision API calls, parsing, and enrichment
with expiration date estimation. Async-first implementation with proper error handling.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
"""

from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from app.clients import claude_client
from app.database import PantryRepository
from app.utils.ingredient_parser import IngredientParser, IngredientParseError
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

# Image validation constants
MAX_IMAGE_SIZE_MB = 5
SUPPORTED_FORMATS = {"image/jpeg", "image/png", "image/webp"}


class ScannerService:
    """
    Service for processing ingredient scans and enriching ingredient data.
    
    Provides async-first methods for image validation, Vision API coordination,
    parsing, and storage of extracted ingredients.
    """
    
    def __init__(self, repository: PantryRepository):
        """
        Initialize scanner service.
        
        Args:
            repository: PantryRepository instance for storing ingredients
        """
        self.repository = repository
    
    @staticmethod
    def _validate_image(image_bytes: bytes, media_type: str) -> tuple[bool, str]:
        """
        Validate image format and size.
        
        Args:
            image_bytes: Raw image data
            media_type: MIME type of the image
        
        Returns:
            Tuple of (is_valid, error_message)
        
        Validates: Requirement 1.2
        """
        if not image_bytes:
            return False, "Image is empty"
        
        if len(image_bytes) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            return False, f"Image exceeds {MAX_IMAGE_SIZE_MB}MB limit"
        
        if media_type not in SUPPORTED_FORMATS:
            return False, f"Unsupported format. Supported: {', '.join(SUPPORTED_FORMATS)}"
        
        return True, ""
    
    @staticmethod
    def estimate_expiration(ingredient_name: str, acquisition_date: Optional[date] = None) -> date:
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
    
    async def scan_image(
        self,
        image_bytes: bytes,
        scan_type: str,
        media_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """
        Process image scan and extract ingredients with storage.
        
        Coordinates:
        1. Image validation
        2. Vision API call (via claude_client.extract_ingredients)
        3. Response parsing using IngredientParser
        4. Expiration enrichment
        5. Storage in PantryRepository
        
        Args:
            image_bytes: Raw image file bytes
            scan_type: Type of scan ("ingredient" or "receipt")
            media_type: MIME type of the image (default: "image/jpeg")
        
        Returns:
            Dictionary with:
            - success (bool): Whether scan was successful
            - ingredients (List[Dict]): Extracted and stored ingredient data with IDs
            - message (str): Result message
            - raw_count (int): Number of raw ingredients detected
            - stored_count (int): Number of ingredients successfully stored
        
        Validates: Requirements 1.1, 1.2, 1.4, 1.5
        """
        # Validate image
        is_valid, error_msg = self._validate_image(image_bytes, media_type)
        if not is_valid:
            logger.warning("[scanner_service] Image validation failed: %s", error_msg)
            return {
                "success": False,
                "ingredients": [],
                "message": error_msg,
                "raw_count": 0,
                "stored_count": 0,
            }
        
        logger.info(
            "[scanner_service] Processing %s scan (%d bytes, %s)",
            scan_type,
            len(image_bytes),
            media_type
        )
        
        try:
            # Call Claude Vision API via claude_client
            raw_ingredients = await claude_client.extract_ingredients(
                image_bytes=image_bytes,
                media_type=media_type
            )
            
            if not raw_ingredients:
                logger.info("[scanner_service] No ingredients detected in image")
                return {
                    "success": False,
                    "ingredients": [],
                    "message": "No ingredients detected in the image. Try a clearer photo.",
                    "raw_count": 0,
                    "stored_count": 0,
                }
            
            logger.info(
                "[scanner_service] Claude Vision returned %d ingredients",
                len(raw_ingredients)
            )
            
            # Enrich ingredients with expiration estimates and store
            enriched_and_stored = []
            for ingredient in raw_ingredients:
                try:
                    acquisition_date = date.fromisoformat(
                        ingredient.get("acquisition_date", date.today().isoformat())
                    )
                    
                    # Estimate expiration if not provided
                    expiration_date_str = ingredient.get("expiration_date")
                    if expiration_date_str:
                        try:
                            expiration_date = date.fromisoformat(expiration_date_str)
                        except ValueError:
                            expiration_date = self.estimate_expiration(
                                ingredient.get("name", "unknown"),
                                acquisition_date
                            )
                    else:
                        expiration_date = self.estimate_expiration(
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
                    
                    # Store in repository
                    stored = await self.repository.create(enriched_item)
                    enriched_and_stored.append(stored)
                    
                except (ValueError, TypeError) as e:
                    logger.warning(
                        "[scanner_service] Failed to enrich/store ingredient %s: %s",
                        ingredient.get("name", "unknown"),
                        str(e)
                    )
                    continue
                except Exception as e:
                    logger.error(
                        "[scanner_service] Unexpected error storing ingredient: %s",
                        str(e)
                    )
                    continue
            
            logger.info(
                "[scanner_service] Successfully stored %d/%d ingredients",
                len(enriched_and_stored),
                len(raw_ingredients)
            )
            
            return {
                "success": True,
                "ingredients": enriched_and_stored,
                "message": f"Successfully scanned and stored {len(enriched_and_stored)} ingredient(s).",
                "raw_count": len(raw_ingredients),
                "stored_count": len(enriched_and_stored),
            }
        
        except Exception as e:
            logger.error("[scanner_service] Unexpected error during scan: %s", str(e))
            return {
                "success": False,
                "ingredients": [],
                "message": f"Failed to process image: {str(e)}",
                "raw_count": 0,
                "stored_count": 0,
            }
