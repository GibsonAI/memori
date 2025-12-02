import os

from memori._config import Config


def test_is_test_mode():
    config = Config()
    assert config.is_test_mode() is False

    try:
        os.environ["MEMORI_TEST_MODE"] = "1"
        assert config.is_test_mode() is True
    finally:
        del os.environ["MEMORI_TEST_MODE"]


def test_reset_cache():
    config = Config()
    config.cache.conversation_id = 123
    config.cache.entity_id = 456
    config.cache.process_id = 789
    config.cache.session_id = 987

    config.reset_cache()

    assert config.cache.conversation_id is None
    assert config.cache.entity_id is None
    assert config.cache.process_id is None
    assert config.cache.session_id is None


def test_augmentation_default():
    config = Config()
    assert config.augmentation is None


def test_storage_initialization():
    config = Config()
    assert config.storage_config is not None
    assert hasattr(config.storage_config, "cockroachdb")
    assert config.storage_config.cockroachdb is False
