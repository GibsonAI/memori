import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memori._config import Config
from memori._exceptions import QuotaExceededError
from memori.memory.augmentation._manager import Manager
from memori.memory.augmentation.input import AugmentationInput


@pytest.fixture
def mock_conn_factory():
    return MagicMock()


@pytest.fixture
def augmentation_input():
    return AugmentationInput(
        entity_id="user123",
        process_id="test-process",
        conversation_id="1",
        conversation_messages=[{"role": "user", "content": "test"}],
        system_prompt=None,
    )


def test_quota_error_prevents_subsequent_augmentations(
    mock_conn_factory, augmentation_input
):
    if "MEMORI_API_KEY" in os.environ:
        del os.environ["MEMORI_API_KEY"]

    config = Config()
    manager = Manager(config)

    with patch(
        "memori.memory.augmentation.augmentations.memori._augmentation.Api"
    ) as MockApi:
        mock_api_instance = MockApi.return_value
        mock_api_instance.augmentation_async = AsyncMock(
            side_effect=QuotaExceededError("Anonymous user quota exceeded")
        )

        with patch(
            "memori.memory.augmentation._manager.connection_context"
        ) as mock_ctx:
            mock_driver = MagicMock()
            mock_driver.conversation.conn.get_dialect.return_value = "postgresql"
            mock_driver.conversation.read.return_value = None
            mock_driver.entity.create.return_value = 1
            mock_ctx.return_value.__enter__.return_value = (None, None, mock_driver)

            manager.start(mock_conn_factory)

            manager.enqueue(augmentation_input)

            time.sleep(1.0)

            assert manager._quota_error is not None, "Quota error should be stored"

            with pytest.raises(
                QuotaExceededError, match="Anonymous user quota exceeded"
            ):
                manager.enqueue(augmentation_input)


def test_quota_error_does_not_prevent_when_authenticated():
    os.environ["MEMORI_API_KEY"] = "test-key"

    try:
        config = Config()
        manager = Manager(config)

        augmentation_input = AugmentationInput(
            entity_id="user123",
            process_id="test-process",
            conversation_id="1",
            conversation_messages=[{"role": "user", "content": "test"}],
            system_prompt=None,
        )

        with patch(
            "memori.memory.augmentation.augmentations.memori._augmentation.Api"
        ) as MockApi:
            mock_api_instance = MockApi.return_value
            mock_api_instance.augmentation_async = AsyncMock(return_value={})

            with patch(
                "memori.memory.augmentation._manager.connection_context"
            ) as mock_ctx:
                mock_driver = MagicMock()
                mock_driver.conversation.conn.get_dialect.return_value = "postgresql"
                mock_driver.conversation.read.return_value = None
                mock_driver.entity.create.return_value = 1
                mock_ctx.return_value.__enter__.return_value = (None, None, mock_driver)

                manager.start(lambda: MagicMock())

                manager.enqueue(augmentation_input)
                time.sleep(0.5)

                manager.enqueue(augmentation_input)
    finally:
        if "MEMORI_API_KEY" in os.environ:
            del os.environ["MEMORI_API_KEY"]
