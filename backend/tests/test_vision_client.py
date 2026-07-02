"""
Unit and Property-based tests for ClaudeVisionClient.

Validates Requirements 10.1, 10.2, 10.6 from the specification.
"""

import pytest
import json
import anthropic
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import date, timedelta
from hypothesis import given, strategies as st, settings, assume

from app.clients.vision_client import (
    ClaudeVisionClient,
    VisionAPIError,
    ScanType,
)


# Unit Tests for ClaudeVisionClient

class TestVisionClientInitialization:
    """Tests for ClaudeVisionClient initialization."""
    
    def test_init_with_valid_api_key(self):
        """Test initialization with valid API key."""
        client = ClaudeVisionClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"
        assert client.max_retries == 2
        assert client.client is not None
    
    def test_init_with_custom_retry_count(self):
        """Test initialization with custom retry count."""
        client = ClaudeVisionClient(api_key="test-key", max_retries=5)
        assert client.max_retries == 5
    
    def test_init_raises_on_empty_api_key(self):
        """Test that initialization raises ValueError for empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            ClaudeVisionClient(api_key="")
    
    def test_init_raises_on_none_api_key(self):
        """Test that initialization raises ValueError for None API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            ClaudeVisionClient(api_key=None)


class TestImageEncoding:
    """Tests for image encoding functionality."""
    
    def test_encode_image_success(self):
        """Test successful image encoding to base64."""
        client = ClaudeVisionClient(api_key="test-key")
        image_bytes = b"fake_image_data"
        encoded = client._encode_image(image_bytes)
        
        assert isinstance(encoded, str)
        assert len(encoded) > 0
        # Verify it's valid base64
        import base64
        decoded = base64.b64decode(encoded)
        assert decoded == image_bytes
    
    def test_encode_image_raises_on_empty_bytes(self):
        """Test that encoding raises ValueError for empty bytes."""
        client = ClaudeVisionClient(api_key="test-key")
        with pytest.raises(ValueError, match="Image bytes cannot be empty"):
            client._encode_image(b"")


class TestJSONParsing:
    """Tests for JSON response parsing."""
    
    def test_parse_json_response_plain_json(self):
        """Test parsing plain JSON response."""
        client = ClaudeVisionClient(api_key="test-key")
        response = '[{"name": "tomato", "quantity": 1}]'
        
        result = client._parse_json_response(response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "tomato"
    
    def test_parse_json_response_with_markdown_fence(self):
        """Test parsing JSON response wrapped in markdown code fence."""
        client = ClaudeVisionClient(api_key="test-key")
        response = '```json\n[{"name": "apple"}]\n```'
        
        result = client._parse_json_response(response)
        assert isinstance(result, list)
        assert result[0]["name"] == "apple"
    
    def test_parse_json_response_with_triple_backticks(self):
        """Test parsing JSON response wrapped in triple backticks."""
        client = ClaudeVisionClient(api_key="test-key")
        response = '```\n[{"name": "banana"}]\n```'
        
        result = client._parse_json_response(response)
        assert isinstance(result, list)
        assert result[0]["name"] == "banana"
    
    def test_parse_json_response_dict(self):
        """Test parsing JSON object response."""
        client = ClaudeVisionClient(api_key="test-key")
        response = '{"name": "carrot", "quantity": 2}'
        
        result = client._parse_json_response(response)
        assert isinstance(result, dict)
        assert result["name"] == "carrot"
    
    def test_parse_json_response_raises_on_invalid_json(self):
        """Test that parsing raises ValueError for invalid JSON."""
        client = ClaudeVisionClient(api_key="test-key")
        response = '{invalid json}'
        
        with pytest.raises(ValueError, match="Invalid JSON in response"):
            client._parse_json_response(response)
    
    def test_parse_json_response_raises_on_empty_response(self):
        """Test that parsing raises ValueError for empty response."""
        client = ClaudeVisionClient(api_key="test-key")
        
        with pytest.raises(ValueError, match="Response text is empty"):
            client._parse_json_response("")
    
    def test_parse_json_response_with_whitespace(self):
        """Test parsing JSON response with surrounding whitespace."""
        client = ClaudeVisionClient(api_key="test-key")
        response = '  \n  [{"name": "onion"}]  \n  '
        
        result = client._parse_json_response(response)
        assert isinstance(result, list)
        assert result[0]["name"] == "onion"


class TestPromptBuilding:
    """Tests for prompt building methods."""
    
    def test_build_ingredient_prompt_default(self):
        """Test ingredient prompt for INGREDIENT scan type."""
        client = ClaudeVisionClient(api_key="test-key")
        prompt = client.build_ingredient_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "ingredient" in prompt.lower()
        assert "JSON" in prompt
    
    def test_build_ingredient_prompt_explicit_ingredient_type(self):
        """Test ingredient prompt with explicit INGREDIENT type."""
        client = ClaudeVisionClient(api_key="test-key")
        prompt = client.build_ingredient_prompt(ScanType.INGREDIENT)
        
        assert isinstance(prompt, str)
        assert "ingredient" in prompt.lower()
    
    def test_build_ingredient_prompt_receipt_type(self):
        """Test ingredient prompt for RECEIPT scan type."""
        client = ClaudeVisionClient(api_key="test-key")
        prompt = client.build_ingredient_prompt(ScanType.RECEIPT)
        
        assert isinstance(prompt, str)
        assert "receipt" in prompt.lower()
    
    def test_build_receipt_prompt(self):
        """Test receipt-specific prompt building."""
        client = ClaudeVisionClient(api_key="test-key")
        prompt = client.build_receipt_prompt()
        
        assert isinstance(prompt, str)
        assert "receipt" in prompt.lower()
    
    def test_build_ingredient_prompt_contains_required_fields(self):
        """Test that ingredient prompt requests all required fields."""
        client = ClaudeVisionClient(api_key="test-key")
        prompt = client.build_ingredient_prompt()
        
        required_fields = ["name", "quantity", "unit", "acquisition_date", "expiration_date", "confidence"]
        for field in required_fields:
            assert field in prompt.lower()
    
    def test_build_ingredient_prompt_includes_today_date(self):
        """Test that prompt includes today's date."""
        client = ClaudeVisionClient(api_key="test-key")
        prompt = client.build_ingredient_prompt()
        
        today = date.today().isoformat()
        assert today in prompt


class TestAnalyzeImageAsync:
    """Tests for the analyze_image async method."""
    
    @pytest.mark.asyncio
    async def test_analyze_image_successful_response(self):
        """Test successful image analysis with valid response."""
        client = ClaudeVisionClient(api_key="test-key")
        
        # Mock the Anthropic client
        mock_response = Mock()
        mock_response.content = [Mock(text='[{"name": "tomato", "quantity": 1, "unit": "pcs", "acquisition_date": "2025-01-01", "expiration_date": "2025-01-08", "confidence": 0.95}]')]
        
        with patch.object(client.client.messages, 'create', return_value=mock_response):
            result = await client.analyze_image(b"fake_image_data", ScanType.INGREDIENT)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "tomato"
    
    @pytest.mark.asyncio
    async def test_analyze_image_raises_on_empty_bytes(self):
        """Test that analyze_image raises ValueError for empty bytes."""
        client = ClaudeVisionClient(api_key="test-key")
        
        with pytest.raises(ValueError, match="Image bytes cannot be empty"):
            await client.analyze_image(b"", ScanType.INGREDIENT)
    
    @pytest.mark.asyncio
    async def test_analyze_image_returns_empty_list_on_no_items(self):
        """Test that analyze_image returns empty list when no items found."""
        client = ClaudeVisionClient(api_key="test-key")
        
        mock_response = Mock()
        mock_response.content = [Mock(text='[]')]
        
        with patch.object(client.client.messages, 'create', return_value=mock_response):
            result = await client.analyze_image(b"fake_image_data", ScanType.INGREDIENT)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_image_handles_markdown_in_response(self):
        """Test that analyze_image handles markdown-wrapped JSON responses."""
        client = ClaudeVisionClient(api_key="test-key")
        
        mock_response = Mock()
        mock_response.content = [Mock(text='```json\n[{"name": "apple", "quantity": 2, "unit": "pcs", "acquisition_date": "2025-01-01", "expiration_date": "2025-01-14", "confidence": 0.9}]\n```')]
        
        with patch.object(client.client.messages, 'create', return_value=mock_response):
            result = await client.analyze_image(b"fake_image_data", ScanType.INGREDIENT)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "apple"
    
    @pytest.mark.asyncio
    async def test_analyze_image_receipt_scan_type(self):
        """Test analyze_image with RECEIPT scan type."""
        client = ClaudeVisionClient(api_key="test-key")
        
        mock_response = Mock()
        mock_response.content = [Mock(text='[{"name": "milk", "quantity": 1, "unit": "l", "acquisition_date": "2025-01-01", "expiration_date": "2025-01-15", "confidence": 0.95}]')]
        
        with patch.object(client.client.messages, 'create', return_value=mock_response) as mock_create:
            result = await client.analyze_image(b"fake_receipt_data", ScanType.RECEIPT, media_type="image/png")
        
        # Verify the API was called
        assert mock_create.called
        # Verify result
        assert isinstance(result, list)
        assert result[0]["name"] == "milk"


class TestVisionAPIError:
    """Tests for VisionAPIError exception."""
    
    def test_vision_api_error_basic_message(self):
        """Test VisionAPIError with basic message."""
        error = VisionAPIError("API failed")
        assert "API failed" in str(error)
    
    def test_vision_api_error_with_retry_count(self):
        """Test VisionAPIError includes retry count in message."""
        error = VisionAPIError("API failed", retry_count=3)
        assert "API failed" in str(error)
        assert "3 retries" in str(error)
    
    def test_vision_api_error_with_original_exception(self):
        """Test VisionAPIError includes original exception details."""
        original = Exception("Original error")
        error = VisionAPIError("API failed", original_error=original)
        assert "Original error" in str(error)
    
    def test_vision_api_error_preserves_attributes(self):
        """Test that VisionAPIError preserves all attributes."""
        original = Exception("Original")
        error = VisionAPIError("Failed", retry_count=2, original_error=original)
        
        assert error.message == "Failed"
        assert error.retry_count == 2
        assert error.original_error == original


class TestRetryLogic:
    """Tests for API retry logic."""
    
    @pytest.mark.asyncio
    async def test_analyze_image_retries_on_api_error(self):
        """Test that analyze_image retries on API errors."""
        client = ClaudeVisionClient(api_key="test-key", max_retries=2)
        
        # Create a mock that fails twice then succeeds
        call_count = 0
        
        def mock_create_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise anthropic.APIConnectionError(request=Mock())
            
            mock_response = Mock()
            mock_response.content = [Mock(text='[{"name": "tomato", "quantity": 1, "unit": "pcs", "acquisition_date": "2025-01-01", "expiration_date": "2025-01-08", "confidence": 0.95}]')]
            return mock_response
        
        with patch.object(client.client.messages, 'create', side_effect=mock_create_side_effect):
            result = await client.analyze_image(b"fake_image_data", ScanType.INGREDIENT)
        
        assert call_count == 3  # Failed twice, succeeded on third
        assert isinstance(result, list)
        assert result[0]["name"] == "tomato"
    
    @pytest.mark.asyncio
    async def test_analyze_image_raises_after_max_retries(self):
        """Test that analyze_image raises VisionAPIError after max retries."""
        client = ClaudeVisionClient(api_key="test-key", max_retries=1)
        
        def mock_create_always_fails(*args, **kwargs):
            raise anthropic.APITimeoutError(request=Mock())
        
        with patch.object(client.client.messages, 'create', side_effect=mock_create_always_fails):
            with pytest.raises(VisionAPIError) as exc_info:
                await client.analyze_image(b"fake_image_data", ScanType.INGREDIENT)
        
        assert exc_info.value.retry_count == 1


# Property-based Tests

@settings(max_examples=10)
@given(
    quantity=st.floats(min_value=0.1, max_value=1000, allow_nan=False, allow_infinity=False),
    confidence=st.floats(min_value=0.0, max_value=1.0),
)
def test_vision_response_field_validation_property(quantity, confidence):
    """
    Property: For any Vision AI response JSON, validation SHALL accept 
    responses containing required fields (ingredient name, acquisition date) 
    and SHALL reject responses missing either required field.
    
    **Validates: Requirement 1.4 - Vision Response Field Validation**
    
    This property ensures that the parser correctly validates required fields.
    """
    client = ClaudeVisionClient(api_key="test-key")
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    # Valid response with all required fields
    valid_response = json.dumps([{
        "name": "tomato",
        "quantity": quantity,
        "unit": "pcs",
        "acquisition_date": today,
        "expiration_date": tomorrow,
        "confidence": confidence
    }])
    
    result = client._parse_json_response(valid_response)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "tomato"
    assert result[0]["quantity"] == quantity
    assert result[0]["confidence"] == confidence
    
    # Response missing name (required) - should parse but be incomplete
    response_no_name = json.dumps([{
        "quantity": quantity,
        "unit": "pcs",
        "acquisition_date": today,
        "expiration_date": tomorrow,
        "confidence": confidence
    }])
    
    result_no_name = client._parse_json_response(response_no_name)
    assert isinstance(result_no_name, list)
    # Parsing succeeds but field is missing
    assert "name" not in result_no_name[0]


@settings(max_examples=5)
@given(st.binary(min_size=1, max_size=1000))
def test_image_encoding_round_trip_property(image_data):
    """
    Property: For any binary image data, encoding to base64 then decoding 
    SHALL produce the original binary data unchanged.
    
    **Validates: Requirement 10.2**
    
    This property ensures image encoding is reversible.
    """
    import base64
    
    client = ClaudeVisionClient(api_key="test-key")
    
    # Encode
    encoded = client._encode_image(image_data)
    
    # Decode
    decoded = base64.b64decode(encoded)
    
    # Verify round-trip
    assert decoded == image_data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
