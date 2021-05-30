import json
import requests

from contextlib import contextmanager
from unittest.mock import patch

from typing import Any, Dict, List

@contextmanager
def mock_http_conversation(http_data: Dict[str, Any]) -> Any:
    """
    Use this context manager to mock and verify a bot's HTTP
    requests to the third-party API (and provide the correct
    third-party API response. This allows us to test things
    that would require the Internet without it).

    http_data should be fixtures data formatted like the data
    in zulip_bots/zulip_bots/bots/giphy/fixtures/test_normal.json
    """
    def get_response(http_response: Dict[str, Any], http_headers: Dict[str, Any], is_raw_response: bool) -> Any:
        """Creates a fake `requests` Response with a desired HTTP response and
        response headers.
        """
        mock_result = requests.Response()
        if is_raw_response:
            mock_result._content = http_response.encode()  # type: ignore # This modifies a "hidden" attribute.
        else:
            mock_result._content = json.dumps(http_response).encode()
        mock_result.status_code = http_headers.get('status', 200)
        return mock_result

    def assert_called_with_fields(mock_result: Any, http_request: Dict[str, Any], fields: List[str], meta: Dict[str, Any]) -> None:
        """Calls `assert_called_with` on a mock object using an HTTP request.
        Uses `fields` to determine which keys to look for in HTTP request and
        to test; if a key is in `fields`, e.g., 'headers', it will be used in
        the assertion.
        """
        args = {}

        for field in fields:
            if field in http_request:
                args[field] = http_request[field]

        mock_result.assert_called_with(http_request['api_url'], **args)

    try:
        http_request = http_data['request']
        http_response = http_data['response']
        http_headers = http_data['response-headers']
    except KeyError:
        print("ERROR: Failed to find 'request', 'response' or 'response-headers' fields in fixture")
        raise

    meta = http_data.get('meta', {})
    is_raw_response = meta.get('is_raw_response', False)

    http_method = http_request.get('method', 'GET')

    if http_method == 'GET':
        with patch('requests.get') as mock_get:
            mock_get.return_value = get_response(http_response, http_headers, is_raw_response)
            yield
            assert_called_with_fields(
                mock_get,
                http_request,
                ['params', 'headers'],
                meta
            )
    elif http_method == 'PATCH':
        with patch('requests.patch') as mock_patch:
            mock_patch.return_value = get_response(http_response, http_headers, is_raw_response)
            yield
            assert_called_with_fields(
                mock_patch,
                http_request,
                ['params', 'headers', 'json', 'data'],
                meta
            )
    elif http_method == 'PUT':
        with patch('requests.put') as mock_post:
            mock_post.return_value = get_response(http_response, http_headers, is_raw_response)
            yield
            assert_called_with_fields(
                mock_post,
                http_request,
                ['params', 'headers', 'json', 'data'],
                meta
            )
    else:
        with patch('requests.post') as mock_post:
            mock_post.return_value = get_response(http_response, http_headers, is_raw_response)
            yield
            assert_called_with_fields(
                mock_post,
                http_request,
                ['params', 'headers', 'json', 'data'],
                meta
            )

@contextmanager
def mock_request_exception() -> Any:
    def assert_mock_called(mock_result: Any) -> None:
        assert mock_result.called

    with patch('requests.get') as mock_get:
        mock_get.return_value = True
        mock_get.side_effect = requests.exceptions.RequestException
        yield
        assert_mock_called(mock_get)
