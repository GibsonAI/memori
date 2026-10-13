r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from memori._cli import Cli
from memori._config import Config
from memori._network import Api


class Manager:
    def __init__(self, config: Config):
        self.config = config

    def execute(self):
        cli = Cli(self.config)

        response = Api(self.config).get("sdk/quota")

        if not isinstance(response, dict):
            raise ValueError("Unexpected quota response format")

        memories = response.get("memories")
        if not isinstance(memories, dict):
            raise ValueError("Missing or invalid 'memories' field in quota response")

        max_memories = memories.get("max")
        current_memories = memories.get("num")
        if max_memories is None or current_memories is None:
            raise ValueError("Missing 'max' or 'num' field in quota response")

        message = response.get("message")
        if not isinstance(message, str):
            raise ValueError("Missing or invalid 'message' field in quota response")

        cli.notice("Maximum # of Memories: " + f"{max_memories:,}")
        cli.notice("Current # of Memories: " + f"{current_memories:,}\n")
        cli.notice(f"{message}\n")
