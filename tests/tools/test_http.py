import pytest
from unittest.mock import MagicMock, patch
from tools.http import fetch_website_content

def test_fetch_website_content_success():
    mock_response = MagicMock()
    mock_response.text = "<html><body><h1>Test</h1><p>Content</p></body></html>"
    mock_response.raise_for_status.return_value = None
    
    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value = mock_response
        
        content = fetch_website_content("http://example.com")
        assert "Test" in content
        assert "Content" in content

def test_fetch_website_content_selector():
    mock_response = MagicMock()
    mock_response.text = "<html><body><div class='content'>Target</div><div class='other'>Ignore</div></body></html>"
    
    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value = mock_response
        
        content = fetch_website_content("http://example.com", selector=".content")
        assert "Target" in content
        assert "Ignore" not in content

def test_fetch_website_content_error():
    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.side_effect = Exception("Network Error")
        
        content = fetch_website_content("http://example.com")
        assert "Error fetching content" in content
