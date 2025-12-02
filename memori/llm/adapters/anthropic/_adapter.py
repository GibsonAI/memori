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
from memori.llm._utils import llm_is_anthropic


@Registry.register_adapter(llm_is_anthropic)
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
            content = payload["conversation"]["response"].get("content", None)
        except KeyError:
            return []

        response = []
        if content is not None:
            # Unstreamed
            # [
            #   {
            #       "text": "...",
            #       "type": "..."
            #   }
            # ]
            for entry in content:
                response.append(
                    {
                        "role": payload["conversation"]["response"].get("role", None),
                        "text": entry["text"],
                        "type": entry["type"],
                    }
                )
        else:
            # Streamed
            """
            REQUEST FOR CONTRIBUTION

            How do we parse the messages when Anthropic streams the response?
            """
            raise RuntimeError("REQUEST FOR CONTRIBUTION")

        return response
