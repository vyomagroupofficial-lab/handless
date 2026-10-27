import os
import pytest
from handless.security.credentials import (
    store_gemini_api_key,
    get_gemini_api_key,
    delete_gemini_api_key,
    has_gemini_api_key,
)

def test_credentials_flow():
    test_key = "test_ai_studio_key_vyoma_12345"
    
    # Store
    assert store_gemini_api_key(test_key) is True
    assert has_gemini_api_key() is True
    
    # Retrieve
    retrieved = get_gemini_api_key()
    assert retrieved == test_key
    
    # Delete
    assert delete_gemini_api_key() is True
    # Reset env var if it exists during test
    os.environ.pop("GEMINI_API_KEY", None)
    assert get_gemini_api_key() is None
    assert has_gemini_api_key() is False
