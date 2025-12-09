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
    hash_id,
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


def test_hash_id_returns_sha256():
    """Test hash_id returns SHA-256 hex digest."""
    result = hash_id("user_123")

    assert result is not None
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_hash_id_is_consistent():
    """Test hash_id returns same hash for same input."""
    input_value = "user_123"

    hash1 = hash_id(input_value)
    hash2 = hash_id(input_value)

    assert hash1 == hash2


def test_hash_id_different_inputs():
    """Test hash_id returns different hashes for different inputs."""
    hash1 = hash_id("user_123")
    hash2 = hash_id("user_456")

    assert hash1 != hash2


def test_hash_id_none_input():
    """Test hash_id returns None for None input."""
    result = hash_id(None)

    assert result is None


def test_hash_id_empty_string():
    """Test hash_id returns None for empty string."""
    result = hash_id("")

    assert result is None


def test_meta_data_with_hashed_ids():
    """Test MetaData includes entity and process IDs in attribution."""
    from memori.memory.augmentation._models import (
        AttributionData,
        EntityData,
        ProcessData,
    )

    meta = MetaData(
        attribution=AttributionData(
            entity=EntityData(id="hashed_entity"),
            process=ProcessData(id="hashed_process"),
        ),
    )

    assert meta.attribution.entity.id == "hashed_entity"
    assert meta.attribution.process.id == "hashed_process"


def test_augmentation_payload_includes_hashed_ids():
    """Test AugmentationPayload.to_dict() includes hashed entity and process IDs."""
    from memori.memory.augmentation._models import (
        AttributionData,
        EntityData,
        ProcessData,
    )

    conversation = ConversationData(messages=[], summary=None)
    meta = MetaData(
        attribution=AttributionData(
            entity=EntityData(id="abc123"),
            process=ProcessData(id="xyz789"),
        ),
    )

    payload = AugmentationPayload(conversation=conversation, meta=meta)
    result = payload.to_dict()

    assert result["meta"]["attribution"]["entity"]["id"] == "abc123"
    assert result["meta"]["attribution"]["process"]["id"] == "xyz789"
