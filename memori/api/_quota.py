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

        cli.notice("Maximum # of Memories: " + f"{response['memories']['max']:,}")
        cli.notice("Current # of Memories: " + f"{response['memories']['num']:,}\n")
        cli.notice(f"{response['message']}\n")
