r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

import warnings

from memori._config import Config
from memori.memory._writer import Writer


class Manager:
    def __init__(self, config: Config):
        self.config = config

    def execute(self, payload):
        if self.config.enterprise is True:
            warnings.warn(
                "Memori Enterprise is not available yet.",
                RuntimeWarning,
                stacklevel=2,
            )
            # TODO: Implement enterprise mode
            # from memori.memory._collector import Collector
            # Collector(self.config).fire_and_forget(payload)

        Writer(self.config).execute(payload)

        return self
