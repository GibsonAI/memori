r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

import os


class Files:
    def __init__(self):
        self.filename_cluster_id = "id"

    def cluster_dir(self):
        return self.storage_dir() + "/cluster"

    def cluster_id(self):
        return "/".join([self.cluster_dir(), self.filename_cluster_id])

    def makedirs(self):
        os.makedirs(self.cluster_dir(), exist_ok=True)
        return self

    def read_id(self):
        try:
            with open(self.cluster_id()) as f:
                return f.read().lstrip().rstrip()
        except FileNotFoundError:
            return None

    def remove_id(self):
        try:
            os.unlink(self.cluster_id())
        except FileNotFoundError:
            pass

        return self

    def storage_dir(self):
        home = os.environ.get("MEMORI_HOME", None)
        if home is None:
            home = os.environ.get("HOME", None)

        if home is None:
            raise RuntimeError(
                "neither MEMORI_HOME nor HOME environment variable is set"
            )

        return f"{home}/.memori"

    def write_id(self, id):
        self.makedirs()

        with open(self.cluster_id(), "w") as f:
            f.write(id)

        return self
