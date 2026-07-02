"""
Database connection and schema management for RasOI.

This module handles SQLite database initialization, connection management,
and provides the PantryRepository for CRUD operations on pantry items.
"""

import aiosqlite
import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pathlib import Path


class DatabaseConnection:
    """Manages SQLite database connection and initialization."""
    
    def __init__(self, db_path: str = "rasoi.db"):
        """
        Initialize database connection manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
    
    async def initialize(self):
        """
        Initialize database schema with tables, indexes, and triggers.
        Creates the pantry_items table if it doesn't exist.
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Create pantry_items table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pantry_items (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    quantity REAL NOT NULL CHECK(quantity >= 0),
                    unit TEXT NOT NULL,
                    acquisition_date TEXT NOT NULL,
                    expiration_date TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on expiration_date for efficient sorting
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_expiration_date 
                ON pantry_items(expiration_date)
            """)
            
            # Create index on name for efficient lookups
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_name 
                ON pantry_items(name)
            """)
            
            # Create trigger for automatic updated_at timestamp
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS update_pantry_items_updated_at
                AFTER UPDATE ON pantry_items
                FOR EACH ROW
                BEGIN
                    UPDATE pantry_items 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = OLD.id;
                END
            """)

            # cooked_history table — powers Chammach memory (PRD §6b.1)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cooked_history (
                    id TEXT PRIMARY KEY,
                    recipe_title TEXT NOT NULL,
                    ingredients_used TEXT NOT NULL,  -- JSON array of names
                    cooked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_cooked_at
                ON cooked_history(cooked_at DESC)
            """)

            # pantry_scans table — scan history with Supabase Storage image URL (PRD §6b.1)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pantry_scans (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT 'guest',
                    image_path TEXT NOT NULL,
                    scan_type TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_pantry_scans_user
                ON pantry_scans(user_id, created_at DESC)
            """)
            
            await db.commit()
    
    async def get_connection(self) -> aiosqlite.Connection:
        """
        Get a database connection.
        
        Returns:
            An aiosqlite connection instance
        """
        return await aiosqlite.connect(self.db_path)


class PantryRepository:
    """
    Repository for pantry item CRUD operations.
    
    Provides async methods for creating, reading, updating, and deleting
    pantry items from the SQLite database.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize repository with database connection.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        self.db_connection = db_connection
    
    async def create(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new pantry item.
        
        Args:
            item_data: Dictionary containing item fields:
                - name (str): Ingredient name
                - quantity (float): Quantity amount
                - unit (str): Unit of measurement
                - acquisition_date (str): ISO format date
                - expiration_date (str): ISO format date
        
        Returns:
            Dictionary with created item including generated id and timestamps
        
        Raises:
            aiosqlite.IntegrityError: If data violates constraints
        """
        item_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        updated_at = created_at
        
        async with await self.db_connection.get_connection() as db:
            await db.execute("""
                INSERT INTO pantry_items 
                (id, name, quantity, unit, acquisition_date, expiration_date, 
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id,
                item_data['name'],
                item_data['quantity'],
                item_data['unit'],
                item_data['acquisition_date'],
                item_data['expiration_date'],
                created_at,
                updated_at
            ))
            await db.commit()
        
        # Return the created item
        return {
            'id': item_id,
            'name': item_data['name'],
            'quantity': item_data['quantity'],
            'unit': item_data['unit'],
            'acquisition_date': item_data['acquisition_date'],
            'expiration_date': item_data['expiration_date'],
            'created_at': created_at,
            'updated_at': updated_at
        }
    
    async def get_all(self) -> List[Dict[str, Any]]:
        """
        Retrieve all pantry items.
        
        Returns:
            List of dictionaries, each representing a pantry item
        """
        async with await self.db_connection.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, name, quantity, unit, acquisition_date, 
                       expiration_date, created_at, updated_at
                FROM pantry_items
                ORDER BY expiration_date ASC
            """)
            rows = await cursor.fetchall()
            
            # Convert Row objects to dictionaries
            return [dict(row) for row in rows]
    
    async def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single pantry item by ID.
        
        Args:
            item_id: Unique identifier of the item
        
        Returns:
            Dictionary with item data, or None if not found
        """
        async with await self.db_connection.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, name, quantity, unit, acquisition_date, 
                       expiration_date, created_at, updated_at
                FROM pantry_items
                WHERE id = ?
            """, (item_id,))
            row = await cursor.fetchone()
            
            return dict(row) if row else None
    
    async def update(self, item_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a pantry item's fields.
        
        Args:
            item_id: Unique identifier of the item to update
            updates: Dictionary with fields to update (quantity, expiration_date, etc.)
        
        Returns:
            Updated item dictionary, or None if item not found
        
        Raises:
            aiosqlite.IntegrityError: If updates violate constraints
        """
        # Check if item exists
        existing = await self.get_by_id(item_id)
        if not existing:
            return None
        
        # Build dynamic UPDATE query based on provided fields
        update_fields = []
        update_values = []
        
        for field in ['name', 'quantity', 'unit', 'acquisition_date', 'expiration_date']:
            if field in updates:
                update_fields.append(f"{field} = ?")
                update_values.append(updates[field])
        
        if not update_fields:
            # No valid fields to update, return existing item
            return existing
        
        # Add item_id to values for WHERE clause
        update_values.append(item_id)
        
        query = f"""
            UPDATE pantry_items 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        
        async with await self.db_connection.get_connection() as db:
            await db.execute(query, update_values)
            await db.commit()
        
        # Return updated item
        return await self.get_by_id(item_id)
    
    async def delete(self, item_id: str) -> bool:
        """
        Delete a pantry item by ID.
        
        Args:
            item_id: Unique identifier of the item to delete
        
        Returns:
            True if item was deleted, False if item not found
        """
        async with await self.db_connection.get_connection() as db:
            cursor = await db.execute("""
                DELETE FROM pantry_items
                WHERE id = ?
            """, (item_id,))
            await db.commit()
            
            # Check if any rows were affected
            return cursor.rowcount > 0

    async def delete_all(self) -> int:
        """Delete every pantry item. Returns the number of rows removed."""
        async with await self.db_connection.get_connection() as db:
            cursor = await db.execute("DELETE FROM pantry_items")
            await db.commit()
            return cursor.rowcount

    async def delete_by_names(self, names: list[str]) -> int:
        """
        Delete pantry items whose name matches any in the provided list
        (case-insensitive). Returns the number of rows removed.
        """
        if not names:
            return 0
        lower_names = [n.lower() for n in names]
        placeholders = ",".join("?" * len(lower_names))
        async with await self.db_connection.get_connection() as db:
            cursor = await db.execute(
                f"DELETE FROM pantry_items WHERE lower(name) IN ({placeholders})",
                lower_names,
            )
            await db.commit()
            return cursor.rowcount

    async def save_scan_record(
        self, user_id: str, image_path: str, scan_type: str
    ) -> str:
        """
        Persist a scan event to pantry_scans (PRD §6b.1).
        Returns the generated record ID.
        """
        record_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        async with await self.db_connection.get_connection() as db:
            await db.execute(
                """
                INSERT INTO pantry_scans (id, user_id, image_path, scan_type, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (record_id, user_id, image_path, scan_type, created_at),
            )
            await db.commit()
        return record_id

    async def get_scan_history(self, user_id: str = "guest", limit: int = 10) -> list[dict]:
        """Return recent scan records for a user (newest first)."""
        async with await self.db_connection.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, user_id, image_path, scan_type, created_at
                FROM pantry_scans
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def save_cook_history(self, recipe_title: str, ingredients_used: list[str]) -> None:
        """Record a cooked meal in cooked_history for Chammach memory (PRD §6b.1)."""
        import json as _json
        record_id = str(uuid.uuid4())
        cooked_at = datetime.utcnow().isoformat()
        async with await self.db_connection.get_connection() as db:
            await db.execute(
                """
                INSERT INTO cooked_history (id, recipe_title, ingredients_used, cooked_at)
                VALUES (?, ?, ?, ?)
                """,
                (record_id, recipe_title, _json.dumps(ingredients_used), cooked_at),
            )
            await db.commit()

    async def get_cook_history(self, days: int = 7) -> list[dict]:
        """Return cooked meals from the last `days` days, newest first (PRD §8b.3)."""
        import json as _json
        from datetime import timedelta
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        async with await self.db_connection.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, recipe_title, ingredients_used, cooked_at
                FROM cooked_history
                WHERE cooked_at >= ?
                ORDER BY cooked_at DESC
                """,
                (since,),
            )
            rows = await cursor.fetchall()
        result = []
        for row in rows:
            r = dict(row)
            try:
                r["ingredients_used"] = _json.loads(r["ingredients_used"])
            except Exception:
                r["ingredients_used"] = []
            result.append(r)
        return result


# Singleton database connection instance
_db_connection: Optional[DatabaseConnection] = None


async def get_database() -> DatabaseConnection:
    """
    Get or create the singleton database connection.
    
    Returns:
        DatabaseConnection instance
    """
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
        await _db_connection.initialize()
    return _db_connection


async def get_repository() -> PantryRepository:
    """
    Get a PantryRepository instance.
    
    Returns:
        PantryRepository instance with initialized database
    """
    db = await get_database()
    return PantryRepository(db)
