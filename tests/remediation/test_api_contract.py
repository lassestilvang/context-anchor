import pytest
import responses
from contextanchor.api_client import APIClient
from contextanchor.errors import ConfigurationError

@responses.activate
def test_api_client_headers():
    # Mock endpoint
    endpoint = "https://api.example.com"
    client = APIClient(endpoint)
    client.api_key = "test-key"
    
    responses.add(
        responses.GET,
        f"{endpoint}/v1/health",
        json={"status": "ok"},
        status=200
    )
    
    client._request("GET", "/v1/health")
    
    # Verify headers
    request = responses.calls[0].request
    assert request.headers["X-API-Key"] == "test-key"
    assert request.headers["Authorization"] == "Bearer test-key"

def test_api_client_url_normalization():
    # Test cases: (base_endpoint, requested_path, expected_url)
    test_cases = [
        ("https://api.example.com", "/v1/health", "https://api.example.com/v1/health"),
        ("https://api.example.com/", "v1/health", "https://api.example.com/v1/health"),
        ("https://api.example.com/v1", "/v1/health", "https://api.example.com/v1/health"),
        ("https://api.example.com/v1/", "/health", "https://api.example.com/v1/health"),
        ("https://api.example.com/prod/v1", "/v1/health", "https://api.example.com/prod/v1/health"),
    ]
    
    for base, path, expected in test_cases:
        client = APIClient(base)
        # We don't need to actually send the request, just check the constructed URL in _request
        # Mocking requests.Session.request to capture the URL
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, expected, json={}, status=200)
            client._request("GET", path)
            assert rsps.calls[-1].request.url == expected

@responses.activate
def test_api_client_auth_error_handling():
    endpoint = "https://api.example.com"
    client = APIClient(endpoint)
    client.api_key = "invalid-key"
    
    responses.add(
        responses.GET,
        f"{endpoint}/v1/contexts",
        json={"error": "Forbidden"},
        status=403
    )
    
    with pytest.raises(ConfigurationError) as excinfo:
        client.list_contexts(repository_id="repo-1")
    
    assert "Invalid or missing API key" in str(excinfo.value)

@responses.activate
def test_api_client_list_response_parsing():
    # This isn't really testing the client (which just returns raw JSON),
    # but it verifies our assumption that the backend returns 'snapshots'
    endpoint = "https://api.example.com"
    client = APIClient(endpoint)
    
    expected_data = {
        "snapshots": [
            {"snapshot_id": "s1", "captured_at": "2024-01-01T00:00:00Z", "branch": "main", "goals": "test"}
        ],
        "count": 1
    }
    
    responses.add(
        responses.GET,
        f"{endpoint}/v1/contexts",
        json=expected_data,
        status=200
    )
    
    resp = client.list_contexts(repository_id="repo-1")
    assert "snapshots" in resp
    assert len(resp["snapshots"]) == 1
    assert resp["snapshots"][0]["snapshot_id"] == "s1"
