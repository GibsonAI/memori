r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from memori.llm._base import BaseLlmAdaptor
from memori.llm._registry import Registry
from memori.llm._utils import llm_is_deepseek


@Registry.register_adapter(llm_is_deepseek)
class Adapter(BaseLlmAdaptor):
    def get_formatted_query(self, payload):
        """
        [
            {
                "content": "...",
                "role": "..."
            }
        ]
        """

        try:
            messages = payload["conversation"]["query"].get("messages", [])
            return self._exclude_injected_messages(messages, payload)
        except KeyError:
            return []

    def get_formatted_response(self, payload):
        try:
            choices = payload["conversation"]["response"].get("choices", None)
        except KeyError:
            return []

        response = []
        if choices is not None:
            if payload["conversation"]["query"].get("stream", None) is None:
                # Unstreamed
                # [
                #   {
                #       "finish_reason": "...",
                #       "index": ...,
                #       "message": {
                #           "content": "...",
                #           "role": "..."
                #       }
                #   }
                # ]
                for choice in choices:
                    message = choice.get("message", None)
                    if message is not None:
                        content = message.get("content", None)
                        if content is not None:
                            response.append(
                                {
                                    "role": message["role"],
                                    "text": content,
                                    "type": "text",
                                }
                            )
            else:
                # Streamed
                # [
                #   {
                #       "delta": {
                #           "content": "...",
                #           "role": "..."
                #       }
                #   }
                # ]
                content = []
                role = None
                for choice in choices:
                    delta = choice.get("delta", None)
                    if delta is not None:
                        if role is None:
                            role = delta.get("role", None)

                        text_content = delta.get("content", None)
                        if text_content is not None and len(text_content) > 0:
                            content.append(text_content)

                if len(content) > 0:
                    response.append(
                        {"role": role, "text": "".join(content), "type": "text"}
                    )

        return response
