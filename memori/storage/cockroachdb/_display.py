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
    def __init__(self, files: Files | None = None, colorize: bool = False):
        """Display helper for CockroachDB commands.

        Parameters
        ----------
        files: optional Files
            Optional `Files` instance to use (injected for testing). If not
            provided, a default `Files()` will be created.
        colorize: bool
            When True, ASCII color/formatting sequences will be included in
            the returned strings (useful for terminal output). Defaults to
            False for predictable programmatic behavior.
        """
        self.files = files or Files()
        self.colorize = bool(colorize)

    def _color(self, text: str, color: str) -> str:
        """Return text wrapped in simple ANSI color codes when colorize is True.

        Supported colors: 'green', 'yellow', 'blue', 'bold'. If an unknown
        color is requested the text is returned unchanged.
        """
        if not self.colorize:
            return text

        codes = {
            "green": "\x1b[32m",
            "yellow": "\x1b[33m",
            "blue": "\x1b[34m",
            "bold": "\x1b[1m",
            "reset": "\x1b[0m",
        }

        start = codes.get(color, "")
        return f"{start}{text}{codes['reset']}" if start else text

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

    def banner(self):
        """Return the ASCII art banner for CockroachDB helper messages."""
        return __doc__

    def cluster_status(self):
        """Return a user-friendly message describing the current cluster state.

        If a cluster id is present in `Files`, this will include the id and a
        short hint to delete it. Otherwise, it returns the same message as
        :py:meth:`cluster_was_not_started`.
        """
        cid = self.files.read_id()
        if cid:
            cid_str = self._color(cid, "bold")
            return f"""Your active CockroachDB cluster id is: {cid_str}
To delete it, run:

  python -m memori cockroachdb cluster delete
"""

        return self.cluster_was_not_started()

    def connection_string(self):
        """Return a short example connection string for the active cluster.

        If no cluster is active, returns a hint that the user should start one.
        """
        cid = self.files.read_id()
        if cid:
            host = self._color(cid, "green")
            cmd = f"cockroach sql --insecure --host {host}:26257"
            return cmd

        return "No active CockroachDB cluster found. Start one with:\n\n  python -m memori cockroachdb cluster start\n"

    def example_connection_block(self):
        """Return a short multi-line example for connecting to the active cluster."""
        cid = self.files.read_id()
        if cid:
            cmd = self.connection_string()
            return f"To connect to your cluster, run:\n\n  {cmd}\n"

        return "Start a cluster first to see a connection example.\n"

