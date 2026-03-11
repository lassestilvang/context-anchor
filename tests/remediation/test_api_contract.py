import pytest
import responses
from contextanchor.api_client import APIClient


@pytest.fixture
def client():
    return APIClient(api_key="test-key", endpoint="https://api.contextanchor.com/v1")


@responses.activate
def test_api_client_authentication(client):
    responses.add(
        responses.GET,
        "https://api.contextanchor.com/v1/contexts/latest",
        json={"snapshot_id": "test"},
        status=200
    )

    client.get_latest_context("repo", "main")

    assert len(responses.calls) == 1
    headers = responses.calls[0].request.headers
    assert headers["X-API-Key"] == "test-key"
    assert "Authorization" in headers


@responses.activate
def test_api_client_tls_preference(client):
    import ssl
    adapter = client.session.adapters.get("https://")
    assert adapter.min_tls_version in [ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3]


def test_api_url_normalization(client):
    # Test normalization with trailing slash
    client1 = APIClient(endpoint="https://api.com/v1/", api_key="k")
    assert client1.endpoint == "https://api.com/v1"

    # Test normalization without /v1
    client2 = APIClient(endpoint="https://api.com", api_key="k")
    assert client2.endpoint == "https://api.com/v1"

    # Test with /prod/v1
    client3 = APIClient(endpoint="https://api.com/prod/v1", api_key="k")
    assert client3.endpoint == "https://api.com/prod/v1"

    # Test with double /v1/v1 (preventing duplicate path segments)
    client4 = APIClient(endpoint="https://api.com/v1/v1", api_key="k")
    assert client4.endpoint == "https://api.com/v1"


@responses.activate
def test_schema_parity_snapshots_key():
    responses.add(
        responses.GET,
        "https://api.com/v1/contexts",
        json={"snapshots": [], "count": 0},
        status=200
    )

    client = APIClient(api_key="k", endpoint="https://api.com")
    res = client.list_contexts("repo-1")

    assert "snapshots" in res
    assert isinstance(res["snapshots"], list)
