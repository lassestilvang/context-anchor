import pytest
import requests
from unittest.mock import patch, MagicMock

from src.contextanchor.api_client import APIClient
from src.contextanchor.errors import NetworkError, DataError


@pytest.fixture
def api_client():
    with patch("src.contextanchor.api_client.APIClient._load_api_key", return_value="dummy-key"):
        yield APIClient("http://api.example.com")


def test_create_context_success(api_client):
    with patch("requests.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "snapshot_id": "123",
            "captured_at": "2023-01-01T00:00:00Z",
        }
        mock_request.return_value = mock_response

        response = api_client.create_context("repo1", "main", "intent", {})

        assert response["snapshot_id"] == "123"
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args == ("POST", "http://api.example.com/v1/contexts")
        assert kwargs["headers"]["Authorization"] == "Bearer dummy-key"
        assert kwargs["json"]["repository_id"] == "repo1"


def test_api_client_timeout_retry(api_client):
    with patch("requests.request") as mock_request:
        with patch("time.sleep") as mock_sleep:
            # First two fail with timeout, third succeeds
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"snapshot_id": "123"}

            mock_request.side_effect = [
                requests.exceptions.Timeout("Timeout"),
                requests.exceptions.Timeout("Timeout"),
                mock_response,
            ]

            response = api_client.get_context_by_id("123")

            assert response["snapshot_id"] == "123"
            assert mock_request.call_count == 3
            assert mock_sleep.call_count == 2


def test_api_client_timeout_failure(api_client):
    with patch("requests.request") as mock_request:
        with patch("time.sleep"):
            # All fail with timeout
            mock_request.side_effect = requests.exceptions.Timeout("Timeout")

            with pytest.raises(NetworkError, match="Request timed out"):
                api_client.get_context_by_id("123")

            assert mock_request.call_count == 4  # Initial + 3 retries


def test_api_client_http_error_no_retry_400(api_client):
    with patch("requests.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_request.side_effect = http_error

        with pytest.raises(DataError, match="Invalid request"):
            api_client.get_context_by_id("123")

        assert mock_request.call_count == 1  # No retry for 400


def test_list_contexts(api_client):
    with patch("requests.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"snapshots": []}
        mock_request.return_value = mock_response

        api_client.list_contexts("repo1", limit=10, next_token="token")

        args, kwargs = mock_request.call_args
        assert kwargs["params"] == {"repository_id": "repo1", "limit": 10, "next_token": "token"}
