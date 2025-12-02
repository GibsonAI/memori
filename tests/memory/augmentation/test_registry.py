from memori.memory.augmentation._base import BaseAugmentation
from memori.memory.augmentation._registry import Registry


def test_registry_register():
    original_count = len(Registry._augmentations)

    @Registry.register("test_aug")
    class TestAugmentation(BaseAugmentation):
        async def process(self, ctx, driver):
            return ctx

    assert "test_aug" in Registry._augmentations
    assert Registry._augmentations["test_aug"] == TestAugmentation

    del Registry._augmentations["test_aug"]
    assert len(Registry._augmentations) == original_count


def test_registry_augmentations():
    original_augs = Registry._augmentations.copy()
    Registry._augmentations = {}

    @Registry.register("aug1")
    class Aug1(BaseAugmentation):
        async def process(self, ctx, driver):
            return ctx

    @Registry.register("aug2")
    class Aug2(BaseAugmentation):
        async def process(self, ctx, driver):
            return ctx

    registry = Registry()
    augs = registry.augmentations()

    assert len(augs) == 2
    assert isinstance(augs[0], BaseAugmentation)
    assert isinstance(augs[1], BaseAugmentation)

    Registry._augmentations = original_augs
