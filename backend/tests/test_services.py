"""
Unit and Property-based tests for Service Layer.

Tests Scanner, Pantry, Recipe, and Substitution services with mocked AI responses.
Validates end-to-end functionality including storage and parsing coordination.

Validates: Requirements 1.1-1.5, 2.2-2.6, 3.1, 3.4-3.5, 4.5-4.6, 5.1-5.5
"""

import pytest
import asyncio
import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume

from app.services.scanner_service import ScannerService
from app.services.pantry_service import PantryService
from app.services.recipe_service import RecipeService
from app.services.substitution_service import SubstitutionService
from app.database import PantryRepository, DatabaseConnection
import tempfile
import os

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


# =============================================================================
# SCANNER SERVICE TESTS
# =============================================================================

class TestScannerService:
    """Test suite for ScannerService"""
    
    async def test_estimate_expiration_tomato(self):
        """Test expiration estimate for tomato (5 days)."""
        today = date.today()
        result = ScannerService.estimate_expiration("tomato", today)
        assert result == today + timedelta(days=5)
    
    async def test_estimate_expiration_unknown_ingredient(self):
        """Test expiration estimate for unknown ingredient uses default (7 days)."""
        today = date.today()
        result = ScannerService.estimate_expiration("xyzunknown", today)
        assert result == today + timedelta(days=7)
    
    async def test_estimate_expiration_defaults_to_today(self):
        """Test estimate_expiration defaults acquisition_date to today."""
        result = ScannerService.estimate_expiration("milk")
        expected = date.today() + timedelta(days=7)  # milk=7 days
        assert result == expected
    
    async def test_validate_image_accepts_valid_jpeg(self):
        """Test validate_image accepts JPEG."""
        image_bytes = b"fake image data"
        is_valid, error = ScannerService._validate_image(image_bytes, "image/jpeg")
        assert is_valid is True
        assert error == ""
    
    async def test_validate_image_rejects_empty_image(self):
        """Test validate_image rejects empty image."""
        is_valid, error = ScannerService._validate_image(b"", "image/jpeg")
        assert is_valid is False
        assert "empty" in error.lower()
    
    async def test_validate_image_rejects_oversized_image(self):
        """Test validate_image rejects images larger than 5MB."""
        large_image = b"x" * (6 * 1024 * 1024)
        is_valid, error = ScannerService._validate_image(large_image, "image/jpeg")
        assert is_valid is False
        assert "5MB" in error
    
    async def test_validate_image_rejects_unsupported_format(self):
        """Test validate_image rejects unsupported formats."""
        image_bytes = b"fake"
        is_valid, error = ScannerService._validate_image(image_bytes, "image/gif")
        assert is_valid is False
        assert "Unsupported" in error
    
    async def test_scan_image_empty_image_returns_failure(self):
        """Test scan_image returns failure for empty image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = ScannerService(repo)
            
            result = await service.scan_image(b"", "ingredient")
            
            assert result["success"] is False
            assert "empty" in result["message"].lower()
    
    async def test_scan_image_validates_image_format(self):
        """Test scan_image validates image format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = ScannerService(repo)
            
            result = await service.scan_image(b"fake", "ingredient", "image/invalid")
            
            assert result["success"] is False
            assert "Unsupported" in result["message"]
    
    @patch('app.services.scanner_service.claude_client')
    async def test_scan_image_with_mocked_vision_api(self, mock_client):
        """Test scan_image with mocked Vision API response."""
        # Mock Vision API response
        mock_ingredients = [
            {
                "name": "tomato",
                "quantity": 4,
                "unit": "pcs",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=5)).isoformat(),
                "confidence": 0.95,
            }
        ]
        mock_client.extract_ingredients = AsyncMock(return_value=mock_ingredients)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = ScannerService(repo)
            
            fake_image = b"fake image data"
            result = await service.scan_image(fake_image, "ingredient", "image/jpeg")
            
            assert result["success"] is True
            assert result["raw_count"] == 1
            assert result["stored_count"] == 1
            assert len(result["ingredients"]) == 1
            assert result["ingredients"][0]["name"] == "tomato"
            assert result["ingredients"][0]["id"] is not None
            
            # Verify ingredient is in database
            all_items = await repo.get_all()
            assert len(all_items) == 1
            assert all_items[0]["name"] == "tomato"
    
    @patch('app.services.scanner_service.claude_client')
    async def test_scan_image_enriches_expiration_date(self, mock_client):
        """Test scan_image enriches items without expiration dates."""
        mock_ingredients = [
            {
                "name": "bread",
                "quantity": 1,
                "unit": "loaf",
                "acquisition_date": date.today().isoformat(),
                # No expiration_date provided
                "confidence": 0.9,
            }
        ]
        mock_client.extract_ingredients = AsyncMock(return_value=mock_ingredients)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = ScannerService(repo)
            
            result = await service.scan_image(b"fake", "ingredient", "image/jpeg")
            
            assert result["success"] is True
            # bread has 7 day shelf life
            expected_expiry = date.today() + timedelta(days=7)
            assert result["ingredients"][0]["expiration_date"] == expected_expiry.isoformat()
    
    @patch('app.services.scanner_service.claude_client')
    async def test_scan_image_no_ingredients_detected(self, mock_client):
        """Test scan_image handles empty Vision API response."""
        mock_client.extract_ingredients = AsyncMock(return_value=[])
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = ScannerService(repo)
            
            result = await service.scan_image(b"fake", "ingredient", "image/jpeg")
            
            assert result["success"] is False
            assert "no ingredients" in result["message"].lower()


# =============================================================================
# PANTRY SERVICE TESTS
# =============================================================================

class TestPantryService:
    """Test suite for PantryService"""
    
    async def test_add_item_stores_in_repository(self):
        """Test add_item stores item in repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = PantryService(repo)
            
            ingredient_data = {
                "name": "tomato",
                "quantity": 4,
                "unit": "pcs",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=5)).isoformat(),
            }
            
            result = await service.add_item(ingredient_data)
            
            assert result["id"] is not None
            assert result["name"] == "tomato"
            assert "isExpiring" in result
            assert "isExpired" in result
    
    async def test_get_all_items_returns_sorted_by_expiration(self):
        """Test get_all_items returns items sorted by expiration date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = PantryService(repo)
            
            # Add items with different expiration dates
            await service.add_item({
                "name": "milk",
                "quantity": 1,
                "unit": "l",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=10)).isoformat(),
            })
            
            await service.add_item({
                "name": "tomato",
                "quantity": 4,
                "unit": "pcs",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=5)).isoformat(),
            })
            
            items = await service.get_all_items()
            
            assert len(items) == 2
            # tomato (5 days) should come before milk (10 days)
            assert items[0]["name"] == "tomato"
            assert items[1]["name"] == "milk"
    
    async def test_update_item_modifies_quantity(self):
        """Test update_item modifies quantity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = PantryService(repo)
            
            created = await service.add_item({
                "name": "tomato",
                "quantity": 4,
                "unit": "pcs",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=5)).isoformat(),
            })
            
            updated = await service.update_item(created["id"], {"quantity": 2})
            
            assert updated is not None
            assert updated["quantity"] == 2
    
    async def test_update_item_nonexistent_returns_none(self):
        """Test update_item returns None for nonexistent item."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = PantryService(repo)
            
            result = await service.update_item("fake-id", {"quantity": 5})
            
            assert result is None
    
    async def test_delete_item_removes_from_repository(self):
        """Test delete_item removes item from repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = PantryService(repo)
            
            created = await service.add_item({
                "name": "tomato",
                "quantity": 4,
                "unit": "pcs",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=5)).isoformat(),
            })
            
            success = await service.delete_item(created["id"])
            
            assert success is True
            
            # Verify item is gone
            all_items = await service.get_all_items()
            assert len(all_items) == 0
    
    async def test_delete_item_nonexistent_returns_false(self):
        """Test delete_item returns False for nonexistent item."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = PantryService(repo)
            
            result = await service.delete_item("fake-id")
            
            assert result is False
    
    async def test_get_expiring_items_filters_correctly(self):
        """Test get_expiring_items returns items expiring within 3 days."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = PantryService(repo)
            
            # Add fresh item (10 days)
            await service.add_item({
                "name": "milk",
                "quantity": 1,
                "unit": "l",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=10)).isoformat(),
            })
            
            # Add expiring item (2 days)
            await service.add_item({
                "name": "tomato",
                "quantity": 4,
                "unit": "pcs",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=2)).isoformat(),
            })
            
            # Add expired item
            await service.add_item({
                "name": "lettuce",
                "quantity": 1,
                "unit": "bunch",
                "acquisition_date": (date.today() - timedelta(days=10)).isoformat(),
                "expiration_date": (date.today() - timedelta(days=5)).isoformat(),
            })
            
            expiring = await service.get_expiring_items()
            
            # Should return tomato and lettuce
            assert len(expiring) == 2
            names = {item["name"] for item in expiring}
            assert "tomato" in names
            assert "lettuce" in names
    
    async def test_expiry_flags_calculation(self):
        """Test expiry flags (isExpiring, isExpired) are correctly calculated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = PantryService(repo)
            
            # Fresh item
            fresh = await service.add_item({
                "name": "milk",
                "quantity": 1,
                "unit": "l",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=10)).isoformat(),
            })
            assert fresh["isExpiring"] is False
            assert fresh["isExpired"] is False
            
            # Expiring item (2 days)
            expiring = await service.add_item({
                "name": "tomato",
                "quantity": 4,
                "unit": "pcs",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=2)).isoformat(),
            })
            assert expiring["isExpiring"] is True
            assert expiring["isExpired"] is False
            
            # Expired item
            expired = await service.add_item({
                "name": "lettuce",
                "quantity": 1,
                "unit": "bunch",
                "acquisition_date": (date.today() - timedelta(days=10)).isoformat(),
                "expiration_date": (date.today() - timedelta(days=5)).isoformat(),
            })
            assert expired["isExpiring"] is False
            assert expired["isExpired"] is True


# =============================================================================
# RECIPE SERVICE TESTS
# =============================================================================

class TestRecipeService:
    """Test suite for RecipeService"""
    
    @patch('app.services.recipe_service.claude_client')
    async def test_get_recommendations_with_mocked_text_api(self, mock_client):
        """Test get_recommendations with mocked Text API response."""
        mock_recipes = [
            {
                "id": "tomato-curry",
                "name": "Tomato Curry",
                "cuisine": "Indian",
                "difficulty": "Medium",
                "prepTimeMinutes": 30,
                "matchPercentage": 85.0,
                "usesExpiringItems": True,
                "ingredients": [
                    {"name": "tomato", "quantity": 4, "unit": "pcs", "available": True},
                    {"name": "onion", "quantity": 1, "unit": "pcs", "available": False},
                ],
                "missingIngredients": ["onion"],
                "steps": ["Heat oil", "Add tomatoes", "Simmer"],
            }
        ]
        mock_client.get_recipe_recommendations = AsyncMock(return_value=mock_recipes)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = RecipeService(repo)
            
            pantry_items = [
                {
                    "name": "tomato",
                    "quantity": 4,
                    "unit": "pcs",
                    "expiration_date": (date.today() + timedelta(days=2)).isoformat(),
                    "isExpiring": True,
                }
            ]
            
            result = await service.get_recommendations(
                pantry_items=pantry_items,
                prioritize_expiring=True,
                max_recipes=5
            )
            
            assert result["success"] is True
            assert len(result["recipes"]) == 1
            assert result["recipes"][0]["name"] == "Tomato Curry"
    
    async def test_calculate_match_percentage(self):
        """Test calculate_match_percentage computation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = RecipeService(repo)
            
            recipe = {
                "ingredients": [
                    {"name": "tomato", "available": True},
                    {"name": "onion", "available": False},
                    {"name": "salt", "available": True},
                ]
            }
            
            pantry_items = [
                {"name": "tomato", "quantity": 4, "unit": "pcs"},
                {"name": "salt", "quantity": 1, "unit": "cup"},
            ]
            
            enriched_recipe = service.calculate_match_percentage(recipe, pantry_items)
            
            # 2 out of 3 ingredients available = 66.67%
            assert abs(enriched_recipe["matchPercentage"] - 66.67) < 1


# =============================================================================
# SUBSTITUTION SERVICE TESTS
# =============================================================================

class TestSubstitutionService:
    """Test suite for SubstitutionService"""
    
    @patch('app.services.substitution_service.claude_client')
    async def test_get_substitutions_with_mocked_text_api(self, mock_client):
        """Test get_substitutions with mocked Text API response."""
        mock_substitutions = [
            {
                "ingredient": "ghee",
                "ratio": "1:1",
                "notes": "Use same amount as oil",
                "available": True,
            },
            {
                "ingredient": "butter",
                "ratio": "1:0.9",
                "notes": "Slightly less for buttery flavor",
                "available": False,
            },
        ]
        mock_client.get_substitutions = AsyncMock(return_value=mock_substitutions)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = SubstitutionService(repo)
            
            # Add ghee to pantry
            await repo.create({
                "name": "ghee",
                "quantity": 1,
                "unit": "cup",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=30)).isoformat(),
            })
            
            result = await service.get_substitutions(
                missing_ingredient="oil",
                recipe_context="Indian Curry"
            )
            
            assert result["success"] is True
            assert len(result["substitutions"]) == 2
            # ghee should be marked as available
            ghee_sub = next(s for s in result["substitutions"] if s["ingredient"] == "ghee")
            assert ghee_sub["available"] is True
    
    @patch('app.services.substitution_service.claude_client')
    async def test_get_substitutions_empty_pantry(self, mock_client):
        """Test get_substitutions with empty pantry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = SubstitutionService(repo)
            
            result = await service.get_substitutions(
                missing_ingredient="oil",
                recipe_context="Indian Curry"
            )
            
            assert result["success"] is False
            assert "empty" in result["message"].lower()
    
    @patch('app.services.substitution_service.claude_client')
    async def test_get_substitutions_flags_available_items(self, mock_client):
        """Test get_substitutions flags available pantry items."""
        mock_substitutions = [
            {
                "ingredient": "butter",
                "ratio": "1:1",
                "notes": "Direct replacement",
                "available": False,  # Not marked by Claude
            },
        ]
        mock_client.get_substitutions = AsyncMock(return_value=mock_substitutions)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = SubstitutionService(repo)
            
            # Add butter to pantry
            await repo.create({
                "name": "butter",
                "quantity": 1,
                "unit": "cup",
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=90)).isoformat(),
            })
            
            result = await service.get_substitutions(
                missing_ingredient="oil",
                recipe_context="Italian Cooking"
            )
            
            assert result["success"] is True
            # Butter should be marked as available despite Claude saying false
            butter_sub = result["substitutions"][0]
            assert butter_sub["available"] is True


# =============================================================================
# PROPERTY-BASED TESTS
# =============================================================================

class TestServiceProperties:
    """Property-based tests for service layer correctness"""
    
    @given(ingredient_name=st.text(min_size=1, max_size=30))
    @settings(max_examples=50)
    async def test_estimate_expiration_returns_future_date(self, ingredient_name):
        """Property: estimate_expiration always returns a date in the future."""
        assume(ingredient_name.strip())
        
        today = date.today()
        result = ScannerService.estimate_expiration(ingredient_name, today)
        
        assert result > today
        assert result >= today + timedelta(days=2)
    
    @given(
        quantity=st.floats(min_value=0.1, max_value=1000),
        unit=st.sampled_from(["pcs", "g", "ml", "kg", "l", "cup", "tbsp"])
    )
    @settings(max_examples=50)
    async def test_add_item_and_retrieve(self, quantity, unit):
        """Property: Adding an item makes it retrievable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_conn = DatabaseConnection(db_path=db_path)
            await db_conn.initialize()
            repo = PantryRepository(db_conn)
            service = PantryService(repo)
            
            ingredient = {
                "name": "test_ingredient",
                "quantity": quantity,
                "unit": unit,
                "acquisition_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=7)).isoformat(),
            }
            
            added = await service.add_item(ingredient)
            
            # Should be retrievable
            all_items = await service.get_all_items()
            assert len(all_items) >= 1
            
            # Should have same quantity and unit
            retrieved = next(i for i in all_items if i["id"] == added["id"])
            assert abs(retrieved["quantity"] - quantity) < 0.01
            assert retrieved["unit"] == unit
