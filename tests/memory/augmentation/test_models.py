from memori.memory.augmentation._models import (
    AugmentationPayload,
    ConversationData,
    FrameworkData,
    LlmData,
    MetaData,
    ModelData,
    PlatformData,
    SdkData,
    SdkVersionData,
    StorageData,
)


def test_conversation_data_with_summary():
    """Test ConversationData with summary."""
    conversation = ConversationData(
        messages=[{"role": "user", "content": "test"}],
        summary="Test summary",
    )

    assert conversation.messages == [{"role": "user", "content": "test"}]
    assert conversation.summary == "Test summary"


def test_conversation_data_without_summary():
    """Test ConversationData without summary."""
    conversation = ConversationData(
        messages=[{"role": "user", "content": "test"}],
    )

    assert conversation.messages == [{"role": "user", "content": "test"}]
    assert conversation.summary is None


def test_model_data_structure():
    """Test ModelData with SDK version."""
    model = ModelData(
        provider="openai",
        sdk=SdkVersionData(version="2.8.1"),
        version="gpt-4",
    )

    assert model.provider == "openai"
    assert model.sdk.version == "2.8.1"
    assert model.version == "gpt-4"


def test_meta_data_defaults():
    """Test MetaData initializes with defaults."""
    meta = MetaData()

    assert meta.framework.provider is None
    assert meta.llm.model.provider is None
    assert meta.platform.provider is None
    assert meta.sdk.lang == "python"
    assert meta.storage.cockroachdb is False


def test_augmentation_payload_to_dict():
    """Test AugmentationPayload.to_dict() produces correct structure."""
    conversation = ConversationData(
        messages=[{"role": "user", "content": "test"}],
        summary="Test summary",
    )

    meta = MetaData(
        framework=FrameworkData(provider="openai"),
        llm=LlmData(
            model=ModelData(
                provider="openai",
                sdk=SdkVersionData(version="2.8.1"),
                version="gpt-4",
            )
        ),
        platform=PlatformData(provider="nebius"),
        sdk=SdkData(lang="python", version="3.0.3"),
        storage=StorageData(
            cockroachdb=False,
            dialect="postgresql",
        ),
    )

    payload = AugmentationPayload(conversation=conversation, meta=meta)
    result = payload.to_dict()

    assert result["conversation"]["messages"] == [{"role": "user", "content": "test"}]
    assert result["conversation"]["summary"] == "Test summary"
    assert result["meta"]["framework"]["provider"] == "openai"
    assert result["meta"]["llm"]["model"]["provider"] == "openai"
    assert result["meta"]["llm"]["model"]["sdk"]["version"] == "2.8.1"
    assert result["meta"]["llm"]["model"]["version"] == "gpt-4"
    assert result["meta"]["platform"]["provider"] == "nebius"
    assert result["meta"]["sdk"]["lang"] == "python"
    assert result["meta"]["sdk"]["version"] == "3.0.3"
    assert result["meta"]["storage"]["cockroachdb"] is False
    assert result["meta"]["storage"]["dialect"] == "postgresql"


def test_augmentation_payload_with_none_values():
    """Test payload handles None values correctly."""
    conversation = ConversationData(
        messages=[],
        summary=None,
    )

    meta = MetaData(
        framework=FrameworkData(provider=None),
        llm=LlmData(
            model=ModelData(
                provider=None,
                sdk=SdkVersionData(version=None),
                version=None,
            )
        ),
        platform=PlatformData(provider=None),
        sdk=SdkData(lang="python", version=None),
        storage=StorageData(
            cockroachdb=False,
            dialect=None,
        ),
    )

    payload = AugmentationPayload(conversation=conversation, meta=meta)
    result = payload.to_dict()

    assert result["conversation"]["summary"] is None
    assert result["meta"]["framework"]["provider"] is None
    assert result["meta"]["llm"]["model"]["provider"] is None
    assert result["meta"]["llm"]["model"]["sdk"]["version"] is None
    assert result["meta"]["platform"]["provider"] is None


def test_sdk_data_default_lang():
    """Test SdkData defaults to python."""
    sdk = SdkData(version="3.0.3")

    assert sdk.lang == "python"
    assert sdk.version == "3.0.3"


def test_storage_data_defaults():
    """Test StorageData default values."""
    storage = StorageData()

    assert storage.cockroachdb is False
    assert storage.dialect is None
