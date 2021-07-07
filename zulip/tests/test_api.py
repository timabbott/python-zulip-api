import json
import unittest
import responses
import zulip
import urllib

from typing import Any, Tuple, Dict
from unittest import TestCase

class TerminationException(Exception):
    pass

class TestAPI(TestCase):

    @responses.activate
    def test_add_reaction(self) -> None:
        def request_callback(request: Any) -> Tuple[int, Dict[str, str], str]:
            params = {}
            for param in request.body.split("&"):
                key, value = param.split("=")
                params[key] = urllib.parse.unquote(value)
            assert "emoji_name" in params or "emoji_code" in params
            return (200, {}, json.dumps({'result': 'success', 'msg': ''}))

        responses.add_callback(
            method=responses.POST,
            url="https://test.zulipapi.com/api/v1/messages/10/reactions",
            callback=request_callback
        )

        client = zulip.Client(config_file="zulip/tests/test_zuliprc")
        # request with emoji name
        request = {
            "message_id": 10,
            "emoji_name": "octopus",
        }
        result = client.add_reaction(request)
        self.assertEqual(result, {'result': 'success', 'msg': ''})
        # request with emoji code
        request = {
            "message_id": 10,
            "emoji_code": "1f419",
        }
        result = client.add_reaction(request)
        self.assertEqual(result, {'result': 'success', 'msg': ''})

    @responses.activate
    def test_call_on_each_event(self) -> None:

        responses.add(
            responses.POST,
            url="https://test.zulipapi.com/api/v1/register",
            json={'queue_id': '123456789', 'last_event_id': -1, 'msg': '', 'result': 'success'},
            status=200
        )
        responses.add(
            responses.GET,
            url="https://test.zulipapi.com/api/v1/events",
            json={'result': 'success', 'msg': '', 'events': [{'id': 0}, {'id': 1}, {'id': 2}]},
            status=200
        )

        def event_callback(x: Dict[str, Any]) -> None:
            print(x)
            if x['id'] == 2:
                raise TerminationException()

        client = zulip.Client(config_file="zulip/tests/test_zuliprc")

        try:
            client.call_on_each_event(
                event_callback,
            )
        except TerminationException:
            pass

        try:
            client.call_on_each_event(
                event_callback,
                ['message'],
            )
        except TerminationException:
            pass

        try:
            client.call_on_each_event(
                event_callback,
                ['message'],
                [['some', 'narrow']]
            )
        except TerminationException:
            pass

if __name__ == '__main__':
    unittest.main()
