import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memori._config import Config
from memori._exceptions import QuotaExceededError
from memori.memory.augmentation._base import AugmentationContext
from memori.memory.augmentation.augmentations.memori._augmentation import (
    AdvancedAugmentation,
)
from memori.memory.augmentation.input import AugmentationInput


@pytest.mark.asyncio
async def test_quota_exceeded_error_propagates_for_anonymous_users():
    if "MEMORI_API_KEY" in os.environ:
        del os.environ["MEMORI_API_KEY"]

    config = Config()
    augmentation = AdvancedAugmentation(config=config)

    payload = AugmentationInput(
        entity_id="user123",
        process_id="test-process",
        conversation_id="1",
        conversation_messages=[{"role": "user", "content": "test"}],
        system_prompt=None,
    )
    ctx = AugmentationContext(payload=payload)

    mock_driver = MagicMock()
    mock_driver.conversation.conn.get_dialect.return_value = "postgresql"
    mock_driver.conversation.read.return_value = None

    with patch(
        "memori.memory.augmentation.augmentations.memori._augmentation.Api"
    ) as MockApi:
        mock_api_instance = MockApi.return_value
        mock_api_instance.augmentation_async = AsyncMock(
            side_effect=QuotaExceededError("Quota exceeded for anonymous user")
        )

        with pytest.raises(QuotaExceededError) as exc_info:
            await augmentation.process(ctx, mock_driver)

        assert "Quota exceeded for anonymous user" in str(exc_info.value)


@pytest.mark.asyncio
async def test_other_exceptions_caught_gracefully():
    config = Config()
    augmentation = AdvancedAugmentation(config=config)

    payload = AugmentationInput(
        entity_id="user123",
        process_id="test-process",
        conversation_id="1",
        conversation_messages=[{"role": "user", "content": "test"}],
        system_prompt=None,
    )
    ctx = AugmentationContext(payload=payload)

    mock_driver = MagicMock()
    mock_driver.conversation.conn.get_dialect.return_value = "postgresql"
    mock_driver.conversation.read.return_value = None

    with patch(
        "memori.memory.augmentation.augmentations.memori._augmentation.Api"
    ) as MockApi:
        mock_api_instance = MockApi.return_value
        mock_api_instance.augmentation_async = AsyncMock(
            side_effect=RuntimeError("Some other error")
        )

        result = await augmentation.process(ctx, mock_driver)
        assert result == ctx
