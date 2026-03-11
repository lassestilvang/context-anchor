import pytest
import ssl
from unittest.mock import Mock, patch
from src.contextanchor.api_client import APIClient, TLSAdapter

def test_tls_adapter_min_version():
    adapter = TLSAdapter(min_tls_version=ssl.TLSVersion.TLSv1_3)
    assert adapter.min_tls_version == ssl.TLSVersion.TLSv1_3

@patch("ssl.create_default_context")
def test_tls_adapter_init_poolmanager(mock_create_context):
    mock_context = Mock()
    mock_create_context.return_value = mock_context
    
    adapter = TLSAdapter(min_tls_version=ssl.TLSVersion.TLSv1_3)
    
    # Simulate init_poolmanager call
    with patch("requests.adapters.HTTPAdapter.init_poolmanager") as mock_super_init:
        adapter.init_poolmanager(None)
        
        assert mock_create_context.called
        assert mock_context.minimum_version == ssl.TLSVersion.TLSv1_3
        # Check that super().init_poolmanager was called with ssl_context
        called_kwargs = mock_super_init.call_args[1]
        assert "ssl_context" in called_kwargs
        assert called_kwargs["ssl_context"] == mock_context

def test_api_client_session_initialization():
    client = APIClient(endpoint="https://api.example.com")
    assert client.session is not None
    # Check if TLSAdapter is mounted
    assert "https://" in client.session.adapters
    adapter = client.session.adapters["https://"]
    assert isinstance(adapter, TLSAdapter)
    # Check default min version (from implementation it's TLSv1_2)
    assert adapter.min_tls_version == ssl.TLSVersion.TLSv1_2

@patch("requests.Session.request")
def test_api_client_uses_session(mock_request):
    mock_request.return_value = Mock(status_code=200)
    mock_request.return_value.json.return_value = {"status": "ok"}
    
    client = APIClient(endpoint="https://api.example.com")
    client._request("GET", "/test")
    
    # Should call session.request, not requests.request
    assert mock_request.called
    assert mock_request.call_args[0][0] == "GET"
    assert "https://api.example.com/test" in mock_request.call_args[0][1]
