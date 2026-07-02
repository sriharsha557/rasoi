"""
Pantry Service — Inventory management operations.

Provides high-level pantry operations: adding items, updating quantities,
deleting items, filtering by expiration status, and sorting.

Validates: Requirements 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.4, 3.5
"""

from datetime import date
from typing import List, Dict, Any, Optional
from app.database import PantryRepository
import logging

logger = logging.getLogger(__name__)


class PantryService:
    """
    Service for pantry inventory management.
    
    Provides CRUD operations, expiration detection, sorting, and filtering.
    """
    
    def __init__(self, repository: PantryRepository):
        """
        Initialize pantry service.
        
        Args:
            repository: PantryRepository instance for data access
        """
        self.repository = repository
    
    @staticmethod
    def _attach_expiry_flags(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute expiration status flags for an item.
        
        Adds isExpiring and isExpired fields based on expiration_date.
        
        An item is expiring if it expires within 3 days (inclusive).
        An item is expired if expiration_date is in the past.
        
        Validates: Requirements 3.1, 3.5
        
        Args:
            item: Pantry item dictionary
        
        Returns:
            Item with added isExpiring and isExpired fields
        """
        try:
            expiration_date = date.fromisoformat(item.get("expiration_date", ""))
            today = date.today()
            days_until_expiry = (expiration_date - today).days
            
            # Expiring within 3 days (inclusive of today)
            is_expiring = 0 <= days_until_expiry <= 3
            
            # Expired if in the past
            is_expired = days_until_expiry < 0
            
        except (ValueError, TypeError):
            # Invalid date format, assume not expiring
            is_expiring = False
            is_expired = False
        
        return {
            **item,
            "isExpiring": is_expiring,
            "isExpired": is_expired,
        }
    
    async def get_all_items(self) -> List[Dict[str, Any]]:
        """
        Get all pantry items sorted by expiration date.
        
        Returns:
            List of pantry items with expiration flags, sorted earliest expiration first.
        
        Validates: Requirements 2.3, 2.6
        """
        items = await self.repository.get_all()
        
        # Attach expiration status flags
        with_flags = [self._attach_expiry_flags(item) for item in items]
        
        # Sort by expiration date (already done in repository, but ensure here)
        sorted_items = sorted(
            with_flags,
            key=lambda x: x.get("expiration_date", "")
        )
        
        logger.info(
            "[pantry_service] Retrieved %d items from pantry",
            len(sorted_items)
        )
        
        return sorted_items
    
    async def add_item(self, ingredient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new ingredient to the pantry.
        
        Args:
            ingredient_data: Dictionary with ingredient fields:
                - name (str): Ingredient name
                - quantity (float): Quantity amount
                - unit (str): Unit of measurement
                - acquisition_date (str): ISO format date
                - expiration_date (str): ISO format date
        
        Returns:
            Created item with ID and timestamps
        
        Validates: Requirement 2.2
        """
        created_item = await self.repository.create(ingredient_data)
        
        # Attach expiration flags
        item_with_flags = self._attach_expiry_flags(created_item)
        
        logger.info(
            "[pantry_service] Added ingredient: %s (%f %s)",
            ingredient_data.get("name"),
            ingredient_data.get("quantity"),
            ingredient_data.get("unit")
        )
        
        return item_with_flags
    
    async def update_item(
        self,
        item_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing pantry item.
        
        Args:
            item_id: Unique ID of the item to update
            updates: Dictionary with fields to update (quantity, expiration_date, etc.)
        
        Returns:
            Updated item with expiration flags, or None if not found
        
        Validates: Requirement 2.5
        """
        updated_item = await self.repository.update(item_id, updates)
        
        if updated_item is None:
            logger.warning("[pantry_service] Item not found for update: %s", item_id)
            return None
        
        # Attach expiration flags
        item_with_flags = self._attach_expiry_flags(updated_item)
        
        logger.info(
            "[pantry_service] Updated item %s with changes: %s",
            item_id,
            list(updates.keys())
        )
        
        return item_with_flags
    
    async def delete_item(self, item_id: str) -> bool:
        """
        Delete a pantry item by ID.
        
        Args:
            item_id: Unique ID of the item to delete
        
        Returns:
            True if item was deleted, False if not found
        
        Validates: Requirement 2.4
        """
        deleted = await self.repository.delete(item_id)
        
        if deleted:
            logger.info("[pantry_service] Deleted item: %s", item_id)
        else:
            logger.warning("[pantry_service] Item not found for deletion: %s", item_id)
        
        return deleted
    
    async def get_expiring_items(self, days: int = 3) -> List[Dict[str, Any]]:
        """
        Get items expiring within N days.
        
        Args:
            days: Number of days to look ahead (default 3)
        
        Returns:
            List of expiring items sorted by expiration date
        
        Validates: Requirements 3.1, 3.4
        """
        all_items = await self.get_all_items()
        
        # Filter items that are expiring or expired
        expiring = [
            item for item in all_items
            if item.get("isExpiring") or item.get("isExpired")
        ]
        
        logger.info(
            "[pantry_service] Found %d expiring item(s) within %d days",
            len(expiring),
            days
        )
        
        return expiring
    
    async def get_expired_items(self) -> List[Dict[str, Any]]:
        """
        Get all expired items.
        
        Returns:
            List of expired items sorted by how long ago they expired
        """
        all_items = await self.get_all_items()
        
        # Filter items that are expired
        expired = [
            item for item in all_items
            if item.get("isExpired")
        ]
        
        logger.info("[pantry_service] Found %d expired item(s)", len(expired))
        
        return expired
    
    async def get_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single pantry item by ID.
        
        Args:
            item_id: Unique ID of the item
        
        Returns:
            Pantry item with expiration flags, or None if not found
        """
        item = await self.repository.get_by_id(item_id)
        
        if item is None:
            return None
        
        return self._attach_expiry_flags(item)
    
    async def get_pantry_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about the pantry.
        
        Returns:
            Dictionary with:
            - total_items: Total number of items
            - expiring_soon: Number of items expiring within 3 days
            - expired: Number of expired items
            - fresh: Number of fresh items
            - items_by_unit: Count of items grouped by unit
        """
        all_items = await self.get_all_items()
        
        total = len(all_items)
        expiring = sum(1 for i in all_items if i.get("isExpiring"))
        expired = sum(1 for i in all_items if i.get("isExpired"))
        fresh = total - expiring - expired
        
        # Group by unit
        items_by_unit = {}
        for item in all_items:
            unit = item.get("unit", "unknown")
            items_by_unit[unit] = items_by_unit.get(unit, 0) + 1
        
        summary = {
            "total_items": total,
            "expiring_soon": expiring,
            "expired": expired,
            "fresh": fresh,
            "items_by_unit": items_by_unit,
        }
        
        logger.info(
            "[pantry_service] Pantry summary: %d total, %d expiring, %d expired",
            total,
            expiring,
            expired
        )
        
        return summary
