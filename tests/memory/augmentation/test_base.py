import pytest

from memori.memory.augmentation._base import AugmentationContext, BaseAugmentation


def test_base_augmentation_init_default():
    aug = BaseAugmentation()
    assert aug.enabled is True


def test_base_augmentation_init_disabled():
    aug = BaseAugmentation(enabled=False)
    assert aug.enabled is False


@pytest.mark.asyncio
async def test_base_augmentation_process_not_implemented():
    from memori.memory.augmentation.input import AugmentationInput

    aug = BaseAugmentation()
    mock_input = AugmentationInput(
        conversation_id=None, entity_id=None, process_id=None, conversation_messages=[]
    )
    with pytest.raises(NotImplementedError):
        await aug.process(AugmentationContext(payload=mock_input), None)
