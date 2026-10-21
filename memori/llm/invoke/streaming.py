import json
import time

from memori._config import Config
from memori._utils import bytes_to_json
from memori.llm._base import BaseInvoke
from memori.llm._utils import client_is_bedrock
from memori.llm.helpers.serialization import format_kwargs, format_response
from memori.llm.pipelines.post_invoke import format_payload, run_post_invoke


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

        run_post_invoke(
            self.invoke,
            self._kwargs,
            format_payload(
                self.invoke,
                self.config.framework.provider,
                self.config.llm.provider,
                self.config.llm.version,
                self._time_start,
                time.time(),
                format_kwargs(
                    self._kwargs,
                    uses_protobuf=self.invoke._uses_protobuf,
                    framework_provider=self.config.framework.provider,
                    injected_count=self.invoke._injected_message_count,
                ),
                format_response(
                    json.loads(data.decode()), uses_protobuf=self.invoke._uses_protobuf
                ),
            ),
        )

        return data
