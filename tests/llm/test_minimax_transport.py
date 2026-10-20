"""Exercise registered MiniMax clients through real SDK HTTP serialization."""

import copy
import inspect
import json

import anthropic
import httpx
import openai
import pytest

from memori._config import Config
from memori.llm.clients import Anthropic, OpenAi

MODELS = ["MiniMax-M3.1-Flash", "MiniMax-M3", "MiniMax-M2.7", "saved-custom-model"]
HOSTS = ["api.minimax.io", "api.minimaxi.com"]


@pytest.fixture
def config(mocker):
    # Keep registration, invocation, history injection, and SDK serialization real.
    # Persistence after the response is outside this transport test's scope.
    mocker.patch("memori.llm.invoke.invoke.handle_post_response")
    return Config()


def chat_messages():
    return [
        {"role": "user", "content": "Check the weather."},
        {
            "role": "assistant",
            "content": None,
            "reasoning_details": [{"type": "reasoning.text", "text": "Check weather"}],
            "tool_calls": [
                {
                    "id": "call_weather",
                    "type": "function",
                    "function": {"name": "weather", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_weather", "content": "Sunny"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe the scene."},
                {
                    "type": "image_url",
                    "image_url": {"url": "https://example.com/a.png"},
                },
                {
                    "type": "video_url",
                    "video_url": {"url": "https://example.com/a.mp4"},
                },
            ],
        },
    ]


def anthropic_messages():
    return [
        {"role": "user", "content": "Check the weather."},
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "Check weather", "signature": "saved"},
                {
                    "type": "tool_use",
                    "id": "call_weather",
                    "name": "weather",
                    "input": {},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "call_weather",
                    "content": "Sunny",
                },
                {
                    "type": "image",
                    "source": {"type": "url", "url": "https://example.com/a.png"},
                },
            ],
        },
    ]


async def invoke_request(config, protocol, host, asynchronous, payload):
    requests = []

    def handle(request):
        requests.append((request.url, json.loads(request.content)))
        if payload.get("stream"):
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content="data: [DONE]\n\n",
            )
        if protocol == "anthropic":
            response = {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": payload["model"],
                "content": [{"type": "text", "text": "Sunny"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 1},
            }
        elif protocol == "responses":
            response = {
                "id": "resp_test",
                "object": "response",
                "created_at": 0,
                "model": payload["model"],
                "status": "completed",
                "output": [],
            }
        else:
            response = {
                "id": "chat_test",
                "object": "chat.completion",
                "created": 0,
                "model": payload["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Sunny"},
                        "finish_reason": "stop",
                    }
                ],
            }
        return httpx.Response(200, json=response)

    http_class = httpx.AsyncClient if asynchronous else httpx.Client
    http_client = http_class(transport=httpx.MockTransport(handle))
    if protocol == "anthropic":
        sdk_class = anthropic.AsyncAnthropic if asynchronous else anthropic.Anthropic
        client = sdk_class(
            api_key="test-only",
            base_url=f"https://{host}/anthropic",
            http_client=http_client,
        )
        Anthropic(config).register(client)
        create = client.messages.create
        path = "/anthropic/v1/messages"
    else:
        sdk_class = openai.AsyncOpenAI if asynchronous else openai.OpenAI
        client = sdk_class(
            api_key="test-only", base_url=f"https://{host}/v1", http_client=http_client
        )
        OpenAi(config).register(client)
        create = (
            client.responses.create
            if protocol == "responses"
            else client.chat.completions.create
        )
        path = "/v1/responses" if protocol == "responses" else "/v1/chat/completions"
    try:
        result = create(**copy.deepcopy(payload))
        if inspect.isawaitable(result):
            await result
    finally:
        closed = client.close()
        if inspect.isawaitable(closed):
            await closed

    assert config.platform.provider == "minimax"
    assert len(requests) == 1
    url, body = requests[0]
    assert url.host == host
    assert url.path == path
    expected = copy.deepcopy(payload)
    expected.update(expected.pop("extra_body", {}))
    if protocol == "chat" and payload.get("stream"):
        expected["stream_options"] = {"include_usage": True}
    assert body == expected
    return body


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("protocol", ["chat", "anthropic"])
async def test_minimax_preserves_explicit_models_and_history(
    config, model, host, asynchronous, protocol
):
    payload = {"model": model}
    if protocol == "anthropic":
        payload.update(max_tokens=256, messages=anthropic_messages())
    else:
        payload["messages"] = chat_messages()
    body = await invoke_request(config, protocol, host, asynchronous, payload)
    assert "service_tier" not in body
    assert "reasoning_split" not in body
    assert "thinking" not in body
    assert "reasoning_effort" not in body
    assert "output_config" not in body


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_flash_streaming_request(config, host, asynchronous):
    await invoke_request(
        config,
        "chat",
        host,
        asynchronous,
        {
            "model": "MiniMax-M3.1-Flash",
            "messages": chat_messages(),
            "stream": True,
        },
    )


@pytest.mark.parametrize("effort", ["low", "medium", "high", "xhigh", "max"])
@pytest.mark.parametrize("protocol", ["chat", "anthropic", "responses"])
async def test_flash_effort_reaches_transport(config, effort, protocol):
    payload = {"model": "MiniMax-M3.1-Flash"}
    if protocol == "anthropic":
        payload.update(
            max_tokens=256,
            messages=anthropic_messages(),
            extra_body={
                "thinking": {"type": "adaptive"},
                "output_config": {"effort": effort},
            },
        )
    elif protocol == "responses":
        payload.update(input="Hello", reasoning={"effort": effort})
    else:
        payload.update(messages=chat_messages(), reasoning_effort=effort)
    await invoke_request(config, protocol, HOSTS[0], False, payload)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("model", MODELS)
async def test_responses_preserves_client_side_history(config, asynchronous, model):
    # Native Responses support is documented for the international endpoint.
    payload = {
        "model": model,
        "input": [
            {"role": "user", "content": "Check the weather."},
            {
                "type": "reasoning",
                "id": "rs_saved",
                "summary": [{"type": "summary_text", "text": "Check weather"}],
            },
            {
                "type": "function_call",
                "call_id": "call_weather",
                "name": "weather",
                "arguments": "{}",
            },
            {
                "type": "function_call_output",
                "call_id": "call_weather",
                "output": "Sunny",
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": "https://example.com/a.png"}
                ],
            },
        ],
    }
    body = await invoke_request(config, "responses", HOSTS[0], asynchronous, payload)
    assert "previous_response_id" not in body
    assert "conversation" not in body
    assert "store" not in body


@pytest.mark.parametrize("protocol", ["chat", "anthropic"])
async def test_m3_preserves_explicit_disabled_thinking(config, protocol):
    payload = {
        "model": "MiniMax-M3",
        "messages": anthropic_messages()
        if protocol == "anthropic"
        else chat_messages(),
        "extra_body": {"thinking": {"type": "disabled"}},
    }
    if protocol == "anthropic":
        payload["max_tokens"] = 256
    await invoke_request(config, protocol, HOSTS[0], False, payload)
