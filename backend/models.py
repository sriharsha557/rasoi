"""
RasOI Kitchen Intelligence - Pydantic Data Models

This module defines all Pydantic models used throughout the backend application
for data validation, serialization, and API contracts.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import List, Optional
from enum import Enum


class ScanType(str, Enum):
    """Enum for ingredient scanning types."""
    INGREDIENT = "ingredient"
    RECEIPT = "receipt"


class Ingredient(BaseModel):
    """Model for ingredient data extracted from Vision API."""
    name: str
    quantity: float = Field(ge=0.0, description="Quantity must be non-negative")
    unit: str
    acquisition_date: date
    expiration_date: date
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from Vision API (0-1)")


class PantryItem(BaseModel):
    """Model for pantry inventory items with expiration tracking."""
    id: str
    name: str
    quantity: float = Field(ge=0.0, description="Quantity must be non-negative")
    unit: str
    acquisition_date: date
    expiration_date: date
    created_at: datetime
    updated_at: datetime
    
    @property
    def is_expiring(self) -> bool:
        """
        Returns True if item is expiring within 3 days (inclusive).
        
        An item is considered expiring if:
        - It has not yet expired (expiration_date >= today)
        - It expires within 0-3 days from today
        
        Validates: Requirements 3.1
        """
        days_until_expiry = (self.expiration_date - date.today()).days
        return 0 <= days_until_expiry <= 3
    
    @property
    def is_expired(self) -> bool:
        """
        Returns True if expiration date has passed.
        
        An item is expired if its expiration_date is before today.
        
        Validates: Requirements 3.5
        """
        return self.expiration_date < date.today()


class PantryItemUpdate(BaseModel):
    """Model for partial updates to pantry items."""
    quantity: Optional[float] = Field(None, ge=0.0, description="Updated quantity (optional)")
    expiration_date: Optional[date] = Field(None, description="Updated expiration date (optional)")


class RecipeIngredient(BaseModel):
    """Model for ingredients in a recipe with availability status."""
    name: str
    quantity: float = Field(ge=0.0, description="Required quantity for recipe")
    unit: str
    available: bool = Field(description="Whether ingredient is available in pantry")


class Recipe(BaseModel):
    """Model for recipe recommendations."""
    id: str
    name: str
    ingredients: List[RecipeIngredient]
    steps: List[str]
    prep_time_minutes: int = Field(ge=0, description="Preparation time in minutes")
    match_percentage: float = Field(ge=0.0, le=100.0, description="Percentage of available ingredients")
    uses_expiring_items: bool = Field(description="Whether recipe uses expiring ingredients")
    missing_ingredients: List[str] = Field(default_factory=list, description="List of unavailable ingredients")


class Substitution(BaseModel):
    """Model for ingredient substitution suggestions."""
    ingredient: str = Field(description="Substitution ingredient name")
    ratio: str = Field(description="Substitution ratio (e.g., '1:1', '2:1')")
    notes: str = Field(description="Preparation notes for substitution")
    available: bool = Field(description="Whether substitution ingredient is in pantry")


class VisionResponse(BaseModel):
    """Model for raw responses from Claude Vision API."""
    content: str = Field(description="Response content from Vision API")
    model: str = Field(description="Model version used")
    usage: dict = Field(description="API usage statistics")


class TextResponse(BaseModel):
    """Model for raw responses from Claude Text API."""
    content: str = Field(description="Response content from Text API")
    model: str = Field(description="Model version used")
    usage: dict = Field(description="API usage statistics")
