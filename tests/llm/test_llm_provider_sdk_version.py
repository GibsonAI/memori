import pytest

from memori._config import Config
from memori.llm._clients import Anthropic, Google, OpenAi, XAi


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def anthropic_client(config):
    return Anthropic(config)


@pytest.fixture
def google_client(config):
    return Google(config)


@pytest.fixture
def openai_client(config):
    return OpenAi(config)


@pytest.fixture
def xai_client(config):
    return XAi(config)


def test_anthropic_captures_provider_sdk_version(anthropic_client, mocker):
    """Test that Anthropic client captures provider_sdk_version from anthropic module."""
    mock_client = mocker.MagicMock()
    mock_client.messages.create = mocker.MagicMock()
    mock_client.beta.messages.create = mocker.MagicMock()
    del mock_client._memori_installed

    mock_anthropic_module = mocker.MagicMock()
    mock_anthropic_module.__version__ = "0.75.0"
    mocker.patch.dict("sys.modules", {"anthropic": mock_anthropic_module})
    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    anthropic_client.register(mock_client)

    assert anthropic_client.config.llm.provider_sdk_version == "0.75.0"


def test_anthropic_handles_missing_version_gracefully(anthropic_client, mocker):
    """Test that Anthropic client handles missing __version__ gracefully."""
    mock_client = mocker.MagicMock()
    mock_client.messages.create = mocker.MagicMock()
    mock_client.beta.messages.create = mocker.MagicMock()
    del mock_client._memori_installed

    mock_anthropic_module = mocker.MagicMock(spec=[])
    del mock_anthropic_module.__version__
    mocker.patch.dict("sys.modules", {"anthropic": mock_anthropic_module})
    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    anthropic_client.register(mock_client)

    assert anthropic_client.config.llm.provider_sdk_version is None


def test_google_captures_provider_sdk_version(google_client, mocker):
    """Test that Google client captures provider_sdk_version from google.genai module."""
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

    google_client.register(mock_client)

    assert google_client.config.llm.provider_sdk_version == "1.52.0"


def test_google_falls_back_to_importlib_metadata(google_client, mocker):
    """Test that Google client falls back to importlib.metadata.version."""
    mock_client = mocker.MagicMock()
    mock_client.models.generate_content = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.aio

    mock_genai_module = mocker.MagicMock(spec=[])
    del mock_genai_module.__version__

    mock_google_module = mocker.MagicMock()
    mock_google_module.genai = mock_genai_module

    mocker.patch.dict(
        "sys.modules", {"google": mock_google_module, "google.genai": mock_genai_module}
    )

    mock_version = mocker.patch("importlib.metadata.version", return_value="1.52.0")

    google_client.register(mock_client)

    mock_version.assert_called_once_with("google-genai")
    assert google_client.config.llm.provider_sdk_version == "1.52.0"


def test_google_handles_missing_version_gracefully(google_client, mocker):
    """Test that Google client handles missing version gracefully."""
    mock_client = mocker.MagicMock()
    mock_client.models.generate_content = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.aio

    mock_genai_module = mocker.MagicMock(spec=[])
    del mock_genai_module.__version__

    mock_google_module = mocker.MagicMock()
    mock_google_module.genai = mock_genai_module

    mocker.patch.dict(
        "sys.modules", {"google": mock_google_module, "google.genai": mock_genai_module}
    )
    mocker.patch("importlib.metadata.version", side_effect=Exception)

    google_client.register(mock_client)

    assert google_client.config.llm.provider_sdk_version is None


def test_openai_captures_provider_sdk_version_from_client(openai_client, mocker):
    """Test that OpenAI client captures provider_sdk_version from client._version."""
    mock_client = mocker.MagicMock()
    mock_client._version = "2.8.1"
    mock_client.chat.completions.create = mocker.MagicMock()
    mock_client.beta.chat.completions.parse = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.base_url

    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    openai_client.register(mock_client)

    assert openai_client.config.llm.provider_sdk_version == "2.8.1"


def test_xai_captures_provider_sdk_version(xai_client, mocker):
    """Test that XAI client captures provider_sdk_version from xai_sdk module."""
    mock_client = mocker.MagicMock()
    mock_client.chat.create = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.chat.completions

    mock_xai_sdk_module = mocker.MagicMock()
    mock_xai_sdk_module.__version__ = "1.4.1"
    mocker.patch.dict("sys.modules", {"xai_sdk": mock_xai_sdk_module})

    xai_client.register(mock_client)

    assert xai_client.config.llm.provider_sdk_version == "1.4.1"


def test_xai_handles_missing_version_gracefully(xai_client, mocker):
    """Test that XAI client handles missing __version__ gracefully."""
    mock_client = mocker.MagicMock()
    mock_client.chat.create = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.chat.completions

    mock_xai_sdk_module = mocker.MagicMock(spec=[])
    del mock_xai_sdk_module.__version__
    mocker.patch.dict("sys.modules", {"xai_sdk": mock_xai_sdk_module})

    xai_client.register(mock_client)

    assert xai_client.config.llm.provider_sdk_version is None


def test_xai_with_completions_captures_provider_sdk_version(xai_client, mocker):
    """Test that XAI client with completions API captures provider_sdk_version."""
    mock_client = mocker.MagicMock()
    mock_client._version = "1.4.1"
    mock_client.chat.completions.create = mocker.MagicMock()
    mock_client.beta.chat.completions.parse = mocker.MagicMock()
    del mock_client._memori_installed

    mock_xai_sdk_module = mocker.MagicMock()
    mock_xai_sdk_module.__version__ = "1.4.1"
    mocker.patch.dict("sys.modules", {"xai_sdk": mock_xai_sdk_module})
    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    xai_client.register(mock_client)

    assert xai_client.config.llm.provider_sdk_version == "1.4.1"


def test_openai_with_nebius_platform(openai_client, mocker):
    """Test that OpenAI client detects Nebius platform and captures SDK version."""
    mock_client = mocker.MagicMock()
    mock_client._version = "2.8.1"
    mock_client.base_url = "https://api.studio.nebius.com/v1/"
    mock_client.chat.completions.create = mocker.MagicMock()
    mock_client.beta.chat.completions.parse = mocker.MagicMock()
    del mock_client._memori_installed

    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    openai_client.register(mock_client)

    assert openai_client.config.platform.provider == "nebius"
    assert openai_client.config.llm.provider_sdk_version == "2.8.1"


def test_provider_sdk_version_separate_from_model_version(openai_client, mocker):
    """Test that provider_sdk_version is separate from model version (llm.version)."""
    mock_client = mocker.MagicMock()
    mock_client._version = "2.8.1"
    mock_client.chat.completions.create = mocker.MagicMock()
    mock_client.beta.chat.completions.parse = mocker.MagicMock()
    del mock_client._memori_installed
    del mock_client.base_url

    mocker.patch("asyncio.get_running_loop", side_effect=RuntimeError)

    openai_client.register(mock_client)

    # provider_sdk_version should be set during registration
    assert openai_client.config.llm.provider_sdk_version == "2.8.1"

    # llm.version should still be None (set later from kwargs["model"])
    assert openai_client.config.llm.version is None
