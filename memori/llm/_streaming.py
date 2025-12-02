r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

import json
import time

from memori._config import Config
from memori._utils import bytes_to_json
from memori.llm._base import BaseInvoke
from memori.llm._utils import client_is_bedrock
from memori.memory._manager import Manager as MemoryManager


class StreamingBody:
    def __init__(self, config: Config, source_streaming_body):
        self.config = config
        self.source_streaming_body = source_streaming_body
        self.raw_response = None

    def __getattr__(self, name):
        return getattr(self.source_streaming_body, name)

    def configure_invoke(self, invoke: BaseInvoke):
        self.invoke = invoke
        return self

    def configure_request(self, kwargs, time_start):
        self._kwargs = kwargs
        self._time_start = time_start

        if client_is_bedrock(self.config.framework.provider, self.config.llm.provider):
            self._kwargs = bytes_to_json(self._kwargs)

        return self

    def read(self, *args, **kwargs):
        data = self.source_streaming_body.read(*args, **kwargs)

        MemoryManager(self.config).execute(
            self.invoke._format_payload(
                self.config.framework.provider,
                self.config.llm.provider,
                self.config.llm.version,
                self._time_start,
                time.time(),
                self.invoke._format_kwargs(self._kwargs),
                self.invoke._format_response(json.loads(data.decode())),
            )
        )

        return data
