"""
Database connection and schema management for Food Buddy.

Local SQLite holds cook_history (what the user cooked, for Buddy memory)
and user_preferences (onboarding). The pantry itself is session-based and
lives in Supabase's user_last_scan table (see LastScanRepository) — Food Buddy
does not persist a live, continuously-tracked ingredient inventory.
"""

import aiosqlite
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.clients import supabase_client


DEMO_USER_ID = "5d6b4c66-945a-414e-92e4-8fe99ca89e6a"


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
        """Initialize database schema with tables and indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            # cooked_history table — powers Buddy memory (PRD §6b.1)
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

            # user_preferences table — onboarding data for the (single, demo) user
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    cuisines TEXT NOT NULL DEFAULT '[]',        -- JSON array of cuisine names
                    diet_type TEXT NOT NULL DEFAULT 'vegetarian',
                    height_cm REAL,
                    weight_kg REAL,
                    family_size INTEGER NOT NULL DEFAULT 1,
                    budget_amount REAL,
                    budget_period TEXT NOT NULL DEFAULT 'monthly',
                    health_conditions TEXT NOT NULL DEFAULT '[]',  -- JSON array, e.g. ["diabetes"]
                    health_goal TEXT NOT NULL DEFAULT 'maintenance',
                    onboarding_completed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Migration for pre-existing local DBs created before health_conditions/health_goal existed.
            existing_columns = {
                row[1] async for row in await db.execute("PRAGMA table_info(user_preferences)")
            }
            if "health_conditions" not in existing_columns:
                await db.execute("ALTER TABLE user_preferences ADD COLUMN health_conditions TEXT NOT NULL DEFAULT '[]'")
            if "health_goal" not in existing_columns:
                await db.execute("ALTER TABLE user_preferences ADD COLUMN health_goal TEXT NOT NULL DEFAULT 'maintenance'")

            await db.commit()

    async def get_connection(self):
        """
        Get a database connection context manager.

        Returns:
            An aiosqlite connection instance (must be used with async context manager)
        """
        # Return a fresh connection each time - aiosqlite handles the lifecycle
        return aiosqlite.connect(self.db_path)


class CookHistoryRepository:
    """Repository for cooked_history — what the user cooked and when (Buddy memory)."""

    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection

    async def save_cook_history(self, recipe_title: str, ingredients_used: list[str]) -> None:
        """Record a cooked meal in cooked_history for Buddy memory (PRD §6b.1)."""
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


class LastScanRepository:
    """
    Session-based pantry: reads/writes the single most-recent scan per user
    (Supabase user_last_scan). There is no persistent, continuously-tracked
    inventory — every scan (or manual edit) overwrites this one row.
    """

    async def get_last_scan(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Return the user's last scan (items, scan_type, scan_date), or None if they've never scanned."""
        rows = await supabase_client.select_rows(
            "user_last_scan",
            {
                "select": "user_id,scan_date,scan_type,items_json,image_path,updated_at",
                "user_id": f"eq.{user_id}",
                "limit": 1,
            },
        )
        return rows[0] if rows else None

    async def save_last_scan(
        self,
        user_id: str,
        scan_type: str,
        items: List[Dict[str, Any]],
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Overwrite the user's last scan with a new item list (upsert on user_id)."""
        saved = await supabase_client.upsert_rows(
            "user_last_scan",
            [
                {
                    "user_id": user_id,
                    "scan_type": scan_type,
                    "items_json": items,
                    "image_path": image_path,
                    "scan_date": datetime.utcnow().isoformat(),
                }
            ],
            on_conflict="user_id",
        )
        return saved[0] if saved else {}

    async def log_scan_history(
        self, user_id: str, scan_type: str, items: List[Dict[str, Any]]
    ) -> None:
        """
        Append-only record of this scan's items (pantry_scan_history) — not
        used for live pantry state or expiry, purely a signal source for
        future personalization (cuisine affinity, promotions), mirroring how
        receipt_items already drives user_brand_preferences.
        """
        await supabase_client.insert_row(
            "pantry_scan_history",
            {"user_id": user_id, "scan_type": scan_type, "items_json": items},
        )


class PreferencesRepository:
    """Repository for the single-user onboarding preferences (PRD hackathon scope)."""

    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection

    async def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        async with await self.db_connection.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def upsert(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update the preferences row for a user. Returns the saved row."""
        import json as _json

        existing = await self.get(user_id)
        now = datetime.utcnow().isoformat()
        payload = {
            "cuisines": _json.dumps(data["cuisines"]),
            "diet_type": data["diet_type"],
            "height_cm": data["height_cm"],
            "weight_kg": data["weight_kg"],
            "family_size": data["family_size"],
            "budget_amount": data["budget_amount"],
            "budget_period": data["budget_period"],
            "health_conditions": _json.dumps(data.get("health_conditions") or []),
            "health_goal": data.get("health_goal") or "maintenance",
            "onboarding_completed": 1,
        }

        async with await self.db_connection.get_connection() as db:
            if existing:
                await db.execute(
                    """
                    UPDATE user_preferences
                    SET cuisines = ?, diet_type = ?, height_cm = ?, weight_kg = ?,
                        family_size = ?, budget_amount = ?, budget_period = ?,
                        health_conditions = ?, health_goal = ?,
                        onboarding_completed = ?, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (
                        payload["cuisines"], payload["diet_type"], payload["height_cm"],
                        payload["weight_kg"], payload["family_size"], payload["budget_amount"],
                        payload["budget_period"], payload["health_conditions"], payload["health_goal"],
                        payload["onboarding_completed"], now, user_id,
                    ),
                )
            else:
                await db.execute(
                    """
                    INSERT INTO user_preferences
                        (user_id, cuisines, diet_type, height_cm, weight_kg, family_size,
                         budget_amount, budget_period, health_conditions, health_goal,
                         onboarding_completed, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id, payload["cuisines"], payload["diet_type"], payload["height_cm"],
                        payload["weight_kg"], payload["family_size"], payload["budget_amount"],
                        payload["budget_period"], payload["health_conditions"], payload["health_goal"],
                        payload["onboarding_completed"], now, now,
                    ),
                )
            await db.commit()

        return await self.get(user_id)


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


async def get_cook_history_repository() -> CookHistoryRepository:
    """Get a CookHistoryRepository instance backed by the initialized database."""
    db = await get_database()
    return CookHistoryRepository(db)


async def get_last_scan_repository() -> LastScanRepository:
    """Get a LastScanRepository instance (stateless — talks to Supabase directly)."""
    return LastScanRepository()


async def get_preferences_repository() -> PreferencesRepository:
    """Get a PreferencesRepository instance backed by the initialized database."""
    db = await get_database()
    return PreferencesRepository(db)
