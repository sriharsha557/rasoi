"""
Unit tests for ClaudeTextClient.

Tests basic initialization, error handling, and prompt building functionality.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from app.clients.text_client import ClaudeTextClient, TextAPIError


class TestTextAPIError:
    """Test TextAPIError custom exception."""
    
    def test_text_api_error_initialization(self):
        """Test TextAPIError initialization with various parameters."""
        error = TextAPIError("Test error", retry_count=2)
        assert error.message == "Test error"
        assert error.retry_count == 2
        assert error.original_error is None
        
    def test_text_api_error_with_original_exception(self):
        """Test TextAPIError with original exception."""
        original = ValueError("Original error")
        error = TextAPIError("API failed", retry_count=1, original_error=original)
        assert error.original_error is original
        assert error.retry_count == 1


class TestClaudeTextClientInit:
    """Test ClaudeTextClient initialization."""
    
    def test_initialization_with_api_key(self):
        """Test client initialization with provided API key."""
        client = ClaudeTextClient(api_key="test-api-key-123")
        assert client.api_key == "test-api-key-123"
        assert client.max_retries == 2
        assert client.model == "claude-sonnet-4-6"
    
    def test_initialization_with_custom_retries(self):
        """Test client initialization with custom retry count."""
        client = ClaudeTextClient(api_key="test-key", max_retries=5)
        assert client.max_retries == 5
    
    def test_initialization_with_env_variable(self):
        """Test client initialization reading from environment variable."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key-123"}):
            client = ClaudeTextClient()
            assert client.api_key == "env-key-123"
    
    def test_initialization_without_api_key_raises_error(self):
        """Test that initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                ClaudeTextClient()
            assert "ANTHROPIC_API_KEY" in str(exc_info.value)


class TestPromptBuilding:
    """Test prompt building methods."""
    
    def test_build_recipe_prompt_basic(self):
        """Test recipe prompt building with basic ingredients."""
        client = ClaudeTextClient(api_key="test-key")
        prompt = client._build_recipe_prompt(
            ingredients=["tomato", "onion", "garlic"],
            expiring_items=[],
            max_recipes=5
        )
        
        assert "tomato" in prompt
        assert "onion" in prompt
        assert "garlic" in prompt
        assert "Generate 5 meal recipes" in prompt
        assert "JSON array" in prompt
    
    def test_build_recipe_prompt_with_expiring_items(self):
        """Test recipe prompt includes expiring item prioritization."""
        client = ClaudeTextClient(api_key="test-key")
        prompt = client._build_recipe_prompt(
            ingredients=["tomato", "onion"],
            expiring_items=["tomato"],
            max_recipes=3
        )
        
        assert "tomato" in prompt
        assert "PRIORITY INSTRUCTION" in prompt
        assert "Prioritize recipes" in prompt
        assert "expiring" in prompt.lower()
    
    def test_build_recipe_prompt_no_ingredients(self):
        """Test recipe prompt with empty ingredient list."""
        client = ClaudeTextClient(api_key="test-key")
        prompt = client._build_recipe_prompt(
            ingredients=[],
            expiring_items=[],
            max_recipes=5
        )
        
        assert "none" in prompt.lower()
        assert "JSON array" in prompt
    
    def test_build_substitution_prompt_basic(self):
        """Test substitution prompt building."""
        client = ClaudeTextClient(api_key="test-key")
        prompt = client._build_substitution_prompt(
            missing_ingredient="cream",
            recipe_context="Pasta Carbonara",
            available_ingredients=["milk", "butter", "egg"]
        )
        
        assert "cream" in prompt
        assert "Pasta Carbonara" in prompt
        assert "milk" in prompt
        assert "butter" in prompt
        assert "egg" in prompt
        assert "Suggest" in prompt
        assert "ratio" in prompt.lower()
    
    def test_build_substitution_prompt_no_alternatives(self):
        """Test substitution prompt with no available alternatives."""
        client = ClaudeTextClient(api_key="test-key")
        prompt = client._build_substitution_prompt(
            missing_ingredient="saffron",
            recipe_context="Risotto",
            available_ingredients=[]
        )
        
        assert "saffron" in prompt
        assert "Risotto" in prompt
        assert "no other ingredients" in prompt.lower()


class TestJSONParsing:
    """Test JSON parsing functionality."""
    
    def test_parse_json_response_plain(self):
        """Test parsing plain JSON response."""
        client = ClaudeTextClient(api_key="test-key")
        response = '[{"id": "1", "name": "test"}]'
        result = client._parse_json_response(response)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "test"
    
    def test_parse_json_response_with_markdown_fences(self):
        """Test parsing JSON response wrapped in markdown fences."""
        client = ClaudeTextClient(api_key="test-key")
        response = """```json
[{"id": "1", "name": "test"}]
```"""
        result = client._parse_json_response(response)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "test"
    
    def test_parse_json_response_with_triple_backticks(self):
        """Test parsing JSON with just triple backticks."""
        client = ClaudeTextClient(api_key="test-key")
        response = """```
{"id": "1", "name": "test"}
```"""
        result = client._parse_json_response(response)
        
        assert isinstance(result, dict)
        assert result["name"] == "test"
    
    def test_parse_json_response_invalid(self):
        """Test that invalid JSON raises ValueError."""
        client = ClaudeTextClient(api_key="test-key")
        response = "not valid json"
        
        with pytest.raises(ValueError) as exc_info:
            client._parse_json_response(response)
        assert "Failed to parse JSON" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
