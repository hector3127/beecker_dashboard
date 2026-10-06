from unittest.mock import MagicMock

import pytest
import requests

from core.integrations.claude_client import (
    API_VERSION,
    MESSAGES_URL,
    ClaudeClient,
    ClaudeConnectionError,
    text_blocks,
)


def test_create_message_sends_key_and_version():
    session = MagicMock()
    session.post.return_value = MagicMock(
        status_code=200, text='{"content":[]}'
    )

    response = ClaudeClient("sk-test", session=session).create_message(
        {"model": "m"},
    )

    kwargs = session.post.call_args.kwargs
    assert session.post.call_args.args == (MESSAGES_URL,)
    assert kwargs["headers"] == {
        "x-api-key": "sk-test",
        "anthropic-version": API_VERSION,
    }
    assert kwargs["json"] == {"model": "m"}
    assert response.status_code == 200
    assert response.json() == {"content": []}


def test_connection_error_does_not_expose_the_key():
    session = MagicMock()
    session.post.side_effect = requests.ConnectionError("sk-test leaked?")

    with pytest.raises(ClaudeConnectionError) as error:
        ClaudeClient("sk-test", session=session).create_message({})

    assert "sk-test" not in error.value.detail


def test_text_blocks_skips_thinking_blocks():
    data = {
        "content": [
            {"type": "thinking", "thinking": "..."},
            {"type": "text", "text": "hola"},
            "basura",
        ],
    }

    assert text_blocks(data) == ["hola"]
    assert text_blocks({"content": None}) == []
