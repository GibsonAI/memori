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
from memori.llm._utils import llm_is_xai


@Registry.register_adapter(llm_is_xai)
class Adapter(BaseLlmAdaptor):
    def get_formatted_query(self, payload):
        try:
            raw_messages = payload["conversation"]["query"].get("messages", [])
        except KeyError:
            return []

        messages = []
        for msg in raw_messages:
            role_str = msg.get("role", "")
            role = None
            if role_str == "ROLE_USER":
                role = "user"
            elif role_str == "ROLE_ASSISTANT":
                role = "assistant"
            elif role_str == "ROLE_SYSTEM":
                role = "system"

            if role is not None:
                content_parts = msg.get("content", [])
                content_texts = []
                for part in content_parts:
                    text = part.get("text", None)
                    if text is not None:
                        content_texts.append(text)

                if len(content_texts) > 0:
                    messages.append({"role": role, "content": " ".join(content_texts)})

        return self._exclude_injected_messages(messages, payload)

    def get_formatted_response(self, payload):
        try:
            response_data = payload["conversation"]["response"]
        except KeyError:
            return []

        response = []
        content = response_data.get("content", None)
        role = response_data.get("role", None)

        if content is not None and role is not None:
            if isinstance(content, str):
                response.append({"role": role, "text": content, "type": "text"})
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text", None)
                        if text is not None:
                            response.append(
                                {"role": role, "text": text, "type": "text"}
                            )
                    elif isinstance(item, str):
                        response.append({"role": role, "text": item, "type": "text"})

        return response
