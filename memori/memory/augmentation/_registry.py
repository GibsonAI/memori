r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""


class Registry:
    _augmentations: dict[str, type] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(augmentation_class: type):
            cls._augmentations[name] = augmentation_class
            return augmentation_class

        return decorator

    def augmentations(self, config=None):
        return [aug_class(config=config) for aug_class in self._augmentations.values()]
