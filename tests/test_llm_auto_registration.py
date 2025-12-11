"""Tests for automatic LLM client detection and registration via llm.register()."""

import pytest

from memori import Memori


@pytest.fixture
def memori_instance(mocker):
    """Create a Memori instance with mocked storage."""
    mock_conn = mocker.MagicMock()
    mocker.patch("memori.storage.Manager.start", return_value=mocker.MagicMock())
    mocker.patch(
        "memori.memory.augmentation.Manager.start", return_value=mocker.MagicMock()
    )
    return Memori(conn=mock_conn)


def test_llm_register_auto_detects_openai_client(memori_instance, mocker):
    """Test that llm.register() auto-detects OpenAI client."""
    mock_client = mocker.MagicMock()
    type(mock_client).__module__ = "openai"
    mock_client._version = "2.8.1"
    mock_client.chat.completions.create = mocker.MagicMock()
    mock_client.beta.chat.completions.parse = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.base_url

    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    result = memori_instance.llm.register(mock_client)

    assert result is memori_instance
    assert hasattr(mock_client, "_memori_installed")
    assert mock_client._memori_installed is True


def test_llm_register_auto_detects_anthropic_client(memori_instance, mocker):
    """Test that llm.register() auto-detects Anthropic client."""
    mock_client = mocker.MagicMock()
    type(mock_client).__module__ = "anthropic"
    mock_client.messages.create = mocker.MagicMock()
    mock_client.beta.messages.create = mocker.MagicMock()
    del mock_client._memori_installed

    mock_anthropic_module = mocker.MagicMock()
    mock_anthropic_module.__version__ = "0.75.0"
    mocker.patch.dict("sys.modules", {"anthropic": mock_anthropic_module})
    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    result = memori_instance.llm.register(mock_client)

    assert result is memori_instance
    assert hasattr(mock_client, "_memori_installed")
    assert mock_client._memori_installed is True


def test_llm_register_auto_detects_google_genai_client(memori_instance, mocker):
    """Test that llm.register() auto-detects Google genai client."""
    mock_client = mocker.MagicMock()
    type(mock_client).__module__ = "google.genai.client"
    mock_client.models.generate_content = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.aio

    mock_genai_module = mocker.MagicMock()
    mock_genai_module.__version__ = "1.52.0"

    mock_google_module = mocker.MagicMock()
    mock_google_module.genai = mock_genai_module

    mocker.patch.dict(
        "sys.modules", {"google": mock_google_module, "google.genai": mock_genai_module}
    )

    result = memori_instance.llm.register(mock_client)

    assert result is memori_instance
    assert hasattr(mock_client, "_memori_installed")
    assert mock_client._memori_installed is True


def test_llm_register_auto_detects_google_generativeai_client(memori_instance, mocker):
    """Test that llm.register() auto-detects Google generativeai client (legacy)."""
    mock_client = mocker.MagicMock()
    type(mock_client).__module__ = "google.generativeai"
    mock_client.models.generate_content = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.aio

    mock_genai_module = mocker.MagicMock()
    mock_genai_module.__version__ = "1.52.0"

    mock_google_module = mocker.MagicMock()
    mock_google_module.genai = mock_genai_module

    mocker.patch.dict(
        "sys.modules", {"google": mock_google_module, "google.genai": mock_genai_module}
    )

    result = memori_instance.llm.register(mock_client)

    assert result is memori_instance
    assert hasattr(mock_client, "_memori_installed")
    assert mock_client._memori_installed is True


def test_llm_register_auto_detects_xai_client(memori_instance, mocker):
    """Test that llm.register() auto-detects XAI client."""
    mock_client = mocker.MagicMock()
    type(mock_client).__module__ = "xai_sdk.client"
    mock_client.chat.create = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.chat.completions

    mock_xai_sdk_module = mocker.MagicMock()
    mock_xai_sdk_module.__version__ = "1.4.1"
    mocker.patch.dict("sys.modules", {"xai_sdk": mock_xai_sdk_module})

    result = memori_instance.llm.register(mock_client)

    assert result is memori_instance
    assert hasattr(mock_client, "_memori_installed")
    assert mock_client._memori_installed is True


def test_llm_register_auto_detects_pydantic_ai_client(memori_instance, mocker):
    """Test that llm.register() auto-detects Pydantic AI client."""
    mock_client = mocker.MagicMock()
    type(mock_client).__module__ = "pydantic_ai.agent"
    mock_client._version = "1.0.0"
    mock_client.chat.completions.create = mocker.MagicMock()
    del mock_client._memori_installed

    result = memori_instance.llm.register(mock_client)

    assert result is memori_instance
    assert hasattr(mock_client, "_memori_installed")
    assert mock_client._memori_installed is True


def test_llm_register_raises_for_unsupported_client(memori_instance, mocker):
    """Test that llm.register() raises RuntimeError for unsupported client types."""
    mock_client = mocker.MagicMock()
    type(mock_client).__module__ = "some.unknown.client"

    with pytest.raises(
        RuntimeError, match="Unsupported LLM client type: some.unknown.client"
    ):
        memori_instance.llm.register(mock_client)


def test_llm_register_returns_memori_instance(memori_instance, mocker):
    """Test that llm.register() returns the Memori instance for chaining."""
    mock_client = mocker.MagicMock()
    type(mock_client).__module__ = "openai"
    mock_client._version = "2.8.1"
    mock_client.chat.completions.create = mocker.MagicMock()
    mock_client.beta.chat.completions.parse = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.base_url

    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    result = memori_instance.llm.register(mock_client)

    assert result is memori_instance
    assert isinstance(result, Memori)


def test_llm_register_allows_chaining(memori_instance, mocker):
    """Test that llm.register() can be chained with attribution()."""
    mock_client = mocker.MagicMock()
    type(mock_client).__module__ = "openai"
    mock_client._version = "2.8.1"
    mock_client.chat.completions.create = mocker.MagicMock()
    mock_client.beta.chat.completions.parse = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.base_url

    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    # Should not raise any exceptions
    result = memori_instance.llm.register(mock_client).attribution(
        entity_id="test_entity", process_id="test_process"
    )

    assert isinstance(result, Memori)
    assert result.config.entity_id == "test_entity"
    assert result.config.process_id == "test_process"


def test_llm_register_handles_multiple_registrations(memori_instance, mocker):
    """Test that multiple calls to llm.register() with the same client don't cause issues."""
    mock_client = mocker.MagicMock()
    type(mock_client).__module__ = "openai"
    mock_client._version = "2.8.1"
    mock_client.chat.completions.create = mocker.MagicMock()
    mock_client.beta.chat.completions.parse = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.base_url

    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    # First registration
    memori_instance.llm.register(mock_client)
    assert mock_client._memori_installed is True

    # Second registration should not cause issues
    memori_instance.llm.register(mock_client)
    assert mock_client._memori_installed is True


def test_llm_register_agno_openai_chat(memori_instance, mocker):
    """Test that llm.register() works with Agno OpenAI models."""
    mock_model = mocker.MagicMock()
    mock_agno_register = mocker.patch.object(memori_instance.agno, "register")

    result = memori_instance.llm.register(openai_chat=mock_model)

    assert result is memori_instance
    mock_agno_register.assert_called_once_with(
        openai_chat=mock_model, claude=None, gemini=None, xai=None
    )


def test_llm_register_agno_claude(memori_instance, mocker):
    """Test that llm.register() works with Agno Claude models."""
    mock_model = mocker.MagicMock()
    mock_agno_register = mocker.patch.object(memori_instance.agno, "register")

    result = memori_instance.llm.register(claude=mock_model)

    assert result is memori_instance
    mock_agno_register.assert_called_once_with(
        openai_chat=None, claude=mock_model, gemini=None, xai=None
    )


def test_llm_register_langchain_chatopenai(memori_instance, mocker):
    """Test that llm.register() works with LangChain ChatOpenAI models."""
    mock_model = mocker.MagicMock()
    mock_langchain_register = mocker.patch.object(memori_instance.langchain, "register")

    result = memori_instance.llm.register(chatopenai=mock_model)

    assert result is memori_instance
    mock_langchain_register.assert_called_once_with(
        chatbedrock=None,
        chatgooglegenai=None,
        chatopenai=mock_model,
        chatvertexai=None,
    )


def test_llm_register_raises_when_mixing_client_and_framework(memori_instance, mocker):
    """Test that llm.register() raises error when mixing direct client and framework."""
    mock_client = mocker.MagicMock()
    mock_model = mocker.MagicMock()

    with pytest.raises(
        RuntimeError,
        match="Cannot mix direct client registration with framework registration",
    ):
        memori_instance.llm.register(client=mock_client, openai_chat=mock_model)


def test_llm_register_raises_when_mixing_agno_and_langchain(memori_instance, mocker):
    """Test that llm.register() raises error when mixing Agno and LangChain."""
    mock_agno_model = mocker.MagicMock()
    mock_langchain_model = mocker.MagicMock()

    with pytest.raises(
        RuntimeError,
        match="Cannot register both Agno and LangChain clients in the same call",
    ):
        memori_instance.llm.register(
            openai_chat=mock_agno_model, chatopenai=mock_langchain_model
        )


def test_llm_register_raises_when_no_arguments(memori_instance):
    """Test that llm.register() raises error when called with no arguments."""
    with pytest.raises(
        RuntimeError, match="No client or framework model provided to register"
    ):
        memori_instance.llm.register()
