r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from memori.memory.augmentation.input import AugmentationInput


class AugmentationContext:
    def __init__(self, payload: AugmentationInput):
        self.payload = payload
        self.data = {}
        self.writes = []

    def add_write(self, method_path: str, *args, **kwargs):
        self.writes.append({"method_path": method_path, "args": args, "kwargs": kwargs})
        return self


class BaseAugmentation:
    def __init__(self, config=None, enabled: bool = True):
        self.config = config
        self.enabled = enabled

    async def process(self, ctx: AugmentationContext, driver) -> AugmentationContext:
        raise NotImplementedError("Augmentation must implement process() method")
