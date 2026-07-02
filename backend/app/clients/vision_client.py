"""
Claude Vision API client for image analysis and ingredient extraction.

Provides structured interface to Claude Sonnet 4 Vision API with retry logic,
error handling, and support for both ingredient photos and receipt analysis.

Requirements: 10.1, 10.2, 10.6
"""

import anthropic
import base64
import json
import re
import logging
from typing import Optional
from datetime import date, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ScanType(str, Enum):
    """Types of image scans supported."""
    INGREDIENT = "ingredient"
    RECEIPT = "receipt"


class VisionAPIError(Exception):
    """Custom exception for Vision API failures."""
    
    def __init__(self, message: str, retry_count: int = 0, original_error: Optional[Exception] = None):
        """
        Initialize VisionAPIError.
        
        Args:
            message: Human-readable error message
            retry_count: Number of retries attempted before failure
            original_error: The underlying exception that caused the failure
        """
        self.message = message
        self.retry_count = retry_count
        self.original_error = original_error
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format the error message with retry information."""
        msg = self.message
        if self.retry_count > 0:
            msg += f" (failed after {self.retry_count} retries)"
        if self.original_error:
            msg += f": {str(self.original_error)}"
        return msg


class ClaudeVisionClient:
    """
    Client for interacting with Claude Sonnet 4 Vision API.
    
    Handles image analysis for ingredient extraction from photos and receipts,
    with automatic retry logic and structured error handling.
    
    Validates: Requirements 10.1, 10.2, 10.6
    """
    
    def __init__(self, api_key: str, max_retries: int = 2):
        """
        Initialize the Vision API client.
        
        Args:
            api_key: Anthropic API key for authentication
            max_retries: Maximum number of retries for API failures (default: 2)
            
        Raises:
            ValueError: If api_key is empty or None
        """
        if not api_key:
            raise ValueError("API key cannot be empty")
        
        self.api_key = api_key
        self.max_retries = max_retries
        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info(f"ClaudeVisionClient initialized with max_retries={max_retries}")
    
    def _encode_image(self, image_bytes: bytes) -> str:
        """
        Encode image bytes to base64 string for API transmission.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Base64-encoded image string
            
        Raises:
            ValueError: If image_bytes is empty
        """
        if not image_bytes:
            raise ValueError("Image bytes cannot be empty")
        return base64.standard_b64encode(image_bytes).decode("utf-8")
    
    def _parse_json_response(self, text: str) -> dict | list:
        """
        Parse JSON from Claude's response, handling markdown code fences.
        
        Claude sometimes wraps JSON in markdown code fences, so we strip them
        and parse the JSON content.
        
        Args:
            text: Raw response text from Claude API
            
        Returns:
            Parsed JSON as dict or list
            
        Raises:
            json.JSONDecodeError: If response is not valid JSON
            ValueError: If response is empty or malformed
        """
        if not text or not text.strip():
            raise ValueError("Response text is empty")
        
        # Strip markdown code fences (```json or ```)
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        cleaned = cleaned.strip()
        
        if not cleaned:
            raise ValueError("Response is empty after removing markdown")
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {e}")
    
    def build_ingredient_prompt(self, scan_type: ScanType = ScanType.INGREDIENT) -> str:
        """
        Build a structured prompt for ingredient extraction from images.
        
        The prompt instructs Claude to analyze images and extract ingredient data
        in a consistent JSON format suitable for parsing and storage.
        
        Args:
            scan_type: Type of scan (INGREDIENT or RECEIPT) to customize the prompt
            
        Returns:
            Formatted prompt string for Claude Vision API
            
        Validates: Requirements 10.2
        """
        today = date.today().isoformat()
        default_expiry = (date.today() + timedelta(days=7)).isoformat()
        
        if scan_type == ScanType.RECEIPT:
            prompt = f"""You are a kitchen AI assistant. Analyze this grocery receipt image and extract all food items purchased.

For each item identified, return a JSON array where each element has:
- "name": item name (string, lowercase)
- "quantity": numeric amount (number, default 1 if not visible)
- "unit": unit of measure like "pcs", "g", "ml", "kg", "l", "bunch", "pack" (string, infer if needed)
- "acquisition_date": the purchase date shown on receipt, or today's date "{today}" if not visible (string, ISO 8601)
- "expiration_date": estimated expiry date based on product type (string, ISO 8601)
- "confidence": your confidence in the extraction 0.0–1.0 (number)

Return ONLY a JSON array (no explanation, no markdown fences, no comments).
If the image is not a receipt or contains no identifiable food items, return an empty array [].

Example format:
[
  {{"name": "milk", "quantity": 1, "unit": "l", "acquisition_date": "{today}", "expiration_date": "{(date.today() + timedelta(days=14)).isoformat()}", "confidence": 0.95}},
  {{"name": "bread", "quantity": 1, "unit": "pcs", "acquisition_date": "{today}", "expiration_date": "{(date.today() + timedelta(days=5)).isoformat()}", "confidence": 0.90}}
]"""
        else:  # ScanType.INGREDIENT (default)
            prompt = f"""You are a kitchen AI assistant. Analyze this image and extract all visible food ingredients, fresh produce, or packaged items.

For each ingredient identified, return a JSON array where each element has:
- "name": ingredient name (string, lowercase)
- "quantity": numeric amount (number, default 1 if not visible)
- "unit": unit of measure like "pcs", "g", "ml", "kg", "l", "bunch", "pack" (string, infer from image if needed)
- "acquisition_date": today's date "{today}" (string, ISO 8601)
- "expiration_date": estimated expiry date based on product type and appearance (string, ISO 8601)
- "confidence": your confidence in the extraction 0.0–1.0 (number, higher if clearly labeled)

Use these typical storage durations as guidelines:
- Fresh vegetables (tomato, lettuce): 3-7 days
- Fresh fruit (apples, oranges): 5-14 days
- Dairy (milk, yogurt): 7-21 days
- Packaged items: infer from package if visible, otherwise 30 days

Return ONLY a JSON array (no explanation, no markdown fences, no comments).
If the image is not food or contains no identifiable ingredients, return an empty array [].

Example format:
[
  {{"name": "tomato", "quantity": 4, "unit": "pcs", "acquisition_date": "{today}", "expiration_date": "{(date.today() + timedelta(days=5)).isoformat()}", "confidence": 0.95}},
  {{"name": "spinach", "quantity": 1, "unit": "bunch", "acquisition_date": "{today}", "expiration_date": "{(date.today() + timedelta(days=3)).isoformat()}", "confidence": 0.85}}
]"""
        
        return prompt
    
    def build_receipt_prompt(self) -> str:
        """
        Build a specialized prompt for receipt image analysis.
        
        Convenience method that returns the prompt for RECEIPT scan type.
        Equivalent to build_ingredient_prompt(ScanType.RECEIPT).
        
        Returns:
            Formatted prompt string for receipt analysis
            
        Validates: Requirements 10.2
        """
        return self.build_ingredient_prompt(ScanType.RECEIPT)
    
    async def analyze_image(
        self,
        image_bytes: bytes,
        scan_type: ScanType = ScanType.INGREDIENT,
        media_type: str = "image/jpeg",
    ) -> dict | list:
        """
        Send image to Claude Vision API and extract ingredient data.
        
        Implements retry logic with exponential backoff for transient failures.
        Parses the JSON response into structured ingredient data.
        
        Args:
            image_bytes: Raw image bytes to analyze
            scan_type: Type of scan (INGREDIENT or RECEIPT)
            media_type: MIME type of image (default: "image/jpeg")
            
        Returns:
            Parsed JSON response as dict or list containing extracted ingredients
            
        Raises:
            VisionAPIError: If API call fails after all retries
            ValueError: If image_bytes is empty or response is invalid
            
        Validates: Requirements 10.2, 10.6
        """
        if not image_bytes:
            raise ValueError("Image bytes cannot be empty")
        
        prompt = self.build_ingredient_prompt(scan_type)
        b64 = self._encode_image(image_bytes)
        
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                logger.debug(
                    f"Calling Claude Vision API (attempt {retry_count + 1}/{self.max_retries + 1}) "
                    f"for {scan_type.value} scan"
                )
                
                message = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": b64,
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                )
                
                raw_response = message.content[0].text
                logger.debug(f"Vision API response received (length: {len(raw_response)})")
                
                # Parse the JSON response
                result = self._parse_json_response(raw_response)
                logger.info(f"Successfully extracted {len(result) if isinstance(result, list) else 1} items")
                
                return result if isinstance(result, list) else []
            
            except (anthropic.APIError, anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
                last_error = e
                
                if retry_count < self.max_retries:
                    retry_count += 1
                    logger.warning(
                        f"Vision API call failed (attempt {retry_count}): {str(e)}. "
                        f"Retrying ({retry_count}/{self.max_retries})..."
                    )
                else:
                    retry_count += 1
                    logger.error(
                        f"Vision API call failed after {retry_count} attempts: {str(e)}"
                    )
                    raise VisionAPIError(
                        f"Vision API call failed after {self.max_retries} retries",
                        retry_count=self.max_retries,
                        original_error=e
                    )
            
            except (ValueError, json.JSONDecodeError) as e:
                # Parsing errors are not retryable
                logger.error(f"Failed to parse Vision API response: {str(e)}")
                raise VisionAPIError(
                    f"Failed to parse Vision API response: {str(e)}",
                    retry_count=retry_count,
                    original_error=e
                )
        
        # This should not be reached, but just in case
        raise VisionAPIError(
            "Vision API call failed: max retries exceeded",
            retry_count=retry_count,
            original_error=last_error
        )
