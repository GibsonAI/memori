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
import sys
import time
from typing import Any

import psycopg
import requests

from memori._cli import Cli
from memori._config import Config
from memori._network import Api
from memori.storage._builder import Builder
from memori.storage._manager import Manager
from memori.storage.cockroachdb._display import Display
from memori.storage.cockroachdb._files import Files


class ClusterManager:
    def __init__(self, config: Config):
        self.config = config
        self.display = Display()
        self.files = Files()

    def claim(self, cli: Cli):
        if not self.cluster_is_started():
            cli.notice(self.display.cluster_was_not_started())
            return self

        cluster_id = self.files.read_id()
        if cluster_id is not None:
            claim = Api(Config()).get(f"cockroachdb/cluster/claim/{cluster_id}")

        cli.notice(
            "You can claim the CockroachDB cluster by using this URL:\n    "
            + claim["url"]
        )
        cli.newline()

        return self

    def delete(self, cli: Cli):
        if not self.cluster_is_started():
            cli.notice(self.display.cluster_was_not_started())
            return self

        cluster_id = self.files.read_id()
        if cluster_id is not None:
            try:
                Api(Config()).delete(f"cockroachdb/cluster/{cluster_id}")
            except requests.exceptions.HTTPError as e:
                if e.response is None or e.response.status_code != 404:
                    raise

        self.files.remove_id()

        cli.notice("The CockroachDB cluster has been deleted.")
        cli.newline()

        return self

    def execute(self):
        cli = Cli(self.config)

        if sys.argv[2] != "cluster" or sys.argv[3] not in ["start", "claim", "delete"]:
            self.usage()
            cli.newline()
            sys.exit(1)

        if sys.argv[3] == "claim":
            self.claim(cli)
        elif sys.argv[3] == "start":
            self.start(cli)
        elif sys.argv[3] == "delete":
            self.delete(cli)

        return self

    def start(self, cli: Cli):
        if self.cluster_is_started():
            cli.notice(self.display.cluster_already_started())
            return self

        cli.print(
            "Before we begin, we want you to know that security and privacy are\n"
            + "very important to us. Once we create this cluster for you we can\n"
            + "never access it again unless you provide us with your connection\n"
            + "string and we cannot help you recover your credentials if you lose\n"
            + "them.\n"
        )

        cli.print("This process may take a minute or longer, please be patient.")

        cli.newline()
        proceed = input("Proceed [Y/n] ")
        cli.newline()

        if proceed is not None and proceed not in ["y", "Y", ""]:
            sys.exit(0)

        cli.notice("[Step 1] Starting new cluster: ", end="")

        started = Api(Config()).post("cockroachdb/cluster/start")

        cli.print("done")

        cli.notice("[Step 2] Waiting for cluster to come online: ", end="")

        finalized: dict[str, Any] | None = None
        for _i in range(24):
            finalized = Api(Config()).post(
                f"cockroachdb/cluster/finalize/{started['cluster']['uuid']}",
                json={"cluster": {"id": started["cluster"]["id"]}},
            )
            if finalized["status"] == 1:
                break

            time.sleep(5)

        if finalized is None or finalized["status"] != 1:
            self.cluster_finalize_failed()
            return

        self.files.write_id(started["cluster"]["uuid"])

        cli.print("done")

        cli.notice("[Step 3] Creating the Memori schema:\n")

        self.config.storage = Manager(self.config).start(
            lambda: psycopg.connect(finalized["connection"]["string"])
        )
        Builder(self.config).disable_banner().execute()

        cli.notice("--- YOUR COCKROACHDB CLUSTER IS READY! ---\n")

        cli.notice("Please save your connection string:")
        cli.notice(finalized["connection"]["string"], 1)
        cli.newline()

        cli.notice("To use your cluster, set the following environment variable:")
        cli.notice(
            f"MEMORI_COCKROACHDB_CONNECTION_STRING={finalized['connection']['string']}",
            1,
        )
        cli.newline()

        cli.notice("You have to claim this database in 7 days or it will be deleted!")
        cli.notice(finalized["claim"]["url"], 1)

        cli.newline()

        cli.notice("You're all set!")
        cli.newline()

    def cluster_finalize_failed(self):
        raise RuntimeError("the cluster failed to come online; please try again")

    def cluster_is_started(self):
        return os.path.isfile(self.files.cluster_id())

    def usage(self):
        print("usage: python -m memori cockroachdb cluster <start | claim | delete>")
