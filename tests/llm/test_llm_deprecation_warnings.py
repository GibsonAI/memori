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


def test_openai_register_shows_deprecation_warning(memori_instance, mocker):
    """Test that memori.openai.register() shows deprecation warning."""
    mock_client = mocker.MagicMock()
    mock_client._version = "1.0.0"
    mock_client.chat.completions.create = mocker.MagicMock()
    mock_client.beta.chat.completions.parse = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.base_url

    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    with pytest.warns(
        DeprecationWarning, match="memori.openai.register\\(\\) is deprecated"
    ):
        memori_instance.openai.register(mock_client)


def test_anthropic_register_shows_deprecation_warning(memori_instance, mocker):
    """Test that memori.anthropic.register() shows deprecation warning."""
    mock_client = mocker.MagicMock()
    mock_client.messages.create = mocker.MagicMock()
    mock_client.beta.messages.create = mocker.MagicMock()
    del mock_client._memori_installed

    mock_anthropic_module = mocker.MagicMock()
    mock_anthropic_module.__version__ = "0.75.0"
    mocker.patch.dict("sys.modules", {"anthropic": mock_anthropic_module})
    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    with pytest.warns(
        DeprecationWarning, match="memori.anthropic.register\\(\\) is deprecated"
    ):
        memori_instance.anthropic.register(mock_client)


def test_google_register_shows_deprecation_warning(memori_instance, mocker):
    """Test that memori.google.register() shows deprecation warning."""
    mock_client = mocker.MagicMock()
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

    with pytest.warns(
        DeprecationWarning, match="memori.google.register\\(\\) is deprecated"
    ):
        memori_instance.google.register(mock_client)


def test_xai_register_shows_deprecation_warning(memori_instance, mocker):
    """Test that memori.xai.register() shows deprecation warning."""
    mock_client = mocker.MagicMock()
    mock_client.chat.create = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.chat.completions

    mock_xai_sdk_module = mocker.MagicMock()
    mock_xai_sdk_module.__version__ = "1.4.1"
    mocker.patch.dict("sys.modules", {"xai_sdk": mock_xai_sdk_module})

    with pytest.warns(
        DeprecationWarning, match="memori.xai.register\\(\\) is deprecated"
    ):
        memori_instance.xai.register(mock_client)


def test_pydantic_ai_register_shows_deprecation_warning(memori_instance, mocker):
    """Test that memori.pydantic_ai.register() shows deprecation warning."""
    mock_client = mocker.MagicMock()
    mock_client._version = "1.0.0"
    mock_client.chat.completions.create = mocker.MagicMock()
    del mock_client._memori_installed

    with pytest.warns(
        DeprecationWarning, match="memori.pydantic_ai.register\\(\\) is deprecated"
    ):
        memori_instance.pydantic_ai.register(mock_client)


def test_langchain_register_shows_deprecation_warning(memori_instance, mocker):
    """Test that memori.langchain.register() shows deprecation warning."""
    mock_chatbedrock = mocker.MagicMock()
    mock_chatbedrock.client.invoke_model = mocker.MagicMock()
    mock_chatbedrock.client.invoke_model_with_response_stream = mocker.MagicMock()
    del mock_chatbedrock.client._memori_installed

    with pytest.warns(
        DeprecationWarning, match="memori.langchain.register\\(\\) is deprecated"
    ):
        memori_instance.langchain.register(chatbedrock=mock_chatbedrock)


def test_agno_register_shows_deprecation_warning(memori_instance, mocker):
    """Test that memori.agno.register() shows deprecation warning."""
    mock_model = mocker.MagicMock()
    type(mock_model).__module__ = "agno.models.openai"

    mock_client = mocker.MagicMock()
    mock_client._version = "1.0.0"
    mock_client.chat.completions.create = mocker.MagicMock()
    mock_client.beta.chat.completions.parse = mocker.MagicMock()
    del mock_client._memori_installed

    mock_model.get_client.return_value = mock_client
    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    with pytest.warns(
        DeprecationWarning, match="memori.agno.register\\(\\) is deprecated"
    ):
        memori_instance.agno.register(openai_chat=mock_model)


def test_llm_register_no_deprecation_warning(memori_instance, mocker):
    """Test that memori.llm.register() does NOT show deprecation warning."""
    mock_client = mocker.MagicMock()
    type(mock_client).__module__ = "openai"
    mock_client._version = "1.0.0"
    mock_client.chat.completions.create = mocker.MagicMock()
    mock_client.beta.chat.completions.parse = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.base_url

    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    # This should NOT raise a DeprecationWarning
    import warnings

    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always")
        memori_instance.llm.register(mock_client)

    # Filter for deprecation warnings related to register methods
    deprecation_warnings = [
        w
        for w in warning_list
        if issubclass(w.category, DeprecationWarning) and "register()" in str(w.message)
    ]
    assert len(deprecation_warnings) == 0, (
        "llm.register() should not emit deprecation warnings"
    )
