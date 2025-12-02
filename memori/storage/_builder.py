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
from memori.storage._registry import Registry


class Builder:
    def __init__(self, config: Config):
        self.cli = Cli(config)
        self.config = config
        self.display_banner = True
        self.registry = Registry()

    def create_data_structures(self):
        if self.display_banner:
            self.cli.banner()

        if self.config.storage is None or self.config.storage.adapter is None:
            return self

        dialect = self.config.storage.adapter.get_dialect()

        try:
            if self.config.storage is None or self.config.storage.driver is None:
                raise RuntimeError("Driver not initialized")

            num = self.config.storage.driver.schema.version.read()
            if num is None:
                num = 0
        except Exception:
            if self._requires_rollback(dialect):
                if (
                    self.config.storage is not None
                    and self.config.storage.adapter is not None
                ):
                    self.config.storage.adapter.rollback()

            num = 0

        self.cli.notice(f"Currently at revision #{num}.")

        migrations = self._get_dialect_family(dialect)
        if migrations is None:
            raise NotImplementedError(
                f"No migration mapping found for dialect: {dialect}."
            )

        if num == max(migrations.keys()):
            self.cli.notice("data structures are up-to-date", 1)
        else:
            while True:
                num += 1
                if num not in migrations:
                    break

                self.cli.notice(f"Building revision #{num}...")

                for migration in migrations[num]:
                    self.cli.notice(migration["description"], 1)
                    if (
                        self.config.storage is not None
                        and self.config.storage.adapter is not None
                    ):
                        operation = migration.get("operations") or migration.get(
                            "operation"
                        )
                        self.config.storage.adapter.execute(operation)
                        self.config.storage.adapter.commit()

            if self.config.storage is None or self.config.storage.driver is None:
                raise RuntimeError("Driver not initialized")

            self.config.storage.driver.schema.version.delete()
            self.config.storage.driver.schema.version.create(num - 1)

            if self.config.storage.adapter is not None:
                self.config.storage.adapter.commit()

        self.cli.notice("Build executed successfully!")
        self.cli.newline()

        return self

    def disable_banner(self):
        self.display_banner = False
        return self

    def execute(self):
        if self.config.storage is None or self.config.storage.adapter is None:
            return self

        dialect = self.config.storage.adapter.get_dialect()
        supported_dialects = self._get_supported_dialects()

        if dialect in supported_dialects:
            self.create_data_structures()
        else:
            raise NotImplementedError(
                f"Unsupported dialect: {dialect}. "
                f"Supported dialects: {supported_dialects}."
            )

        return self

    def _get_supported_dialects(self):
        return list(self.registry._drivers.keys())

    def _get_dialect_family(self, dialect):
        if dialect in self.registry._drivers:
            driver_class = self.registry._drivers[dialect]
            return getattr(driver_class, "migrations", None)

        return None

    def _requires_rollback(self, dialect):
        if dialect in self.registry._drivers:
            driver_class = self.registry._drivers[dialect]
            return getattr(driver_class, "requires_rollback_on_error", False)

        return False
