r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from memori.storage.cockroachdb._files import Files


class Display:
    def __init__(self):
        self.files = Files()

    def cluster_already_started(self):
        return """You already have an active CockroachDB cluster running. To start
  a new one, execute this command first:

    python -m memori cockroachdb cluster delete
"""

    def cluster_was_not_started(self):
        return """You do not have an active CockroachDB cluster running. To start
  a new one, execute this command first:

    python -m memori cockroachdb cluster start
"""
