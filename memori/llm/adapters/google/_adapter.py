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
from memori.llm._utils import llm_is_google


@Registry.register_adapter(llm_is_google)
class Adapter(BaseLlmAdaptor):
    def get_formatted_query(self, payload):
        """
        [
          {
              "parts": [
                  {
                      "text": "..."
                  }
              ],
              "role": "..."
          }
        ]
        """

        messages = []

        try:
            system_instruction = payload["conversation"]["query"].get(
                "systemInstruction", None
            )
        except KeyError:
            system_instruction = None

        if system_instruction is not None:
            parts = system_instruction.get("parts", None)
            content = []
            if parts is not None:
                for part in parts:
                    text = part.get("text", None)
                    if text is not None and len(text) > 0:
                        content.append(text)

            if len(content) > 0:
                messages.append({"content": " ".join(content), "role": "system"})

        try:
            contents = payload["conversation"]["query"].get("contents", None)
        except KeyError:
            return []

        if contents is not None:
            if isinstance(contents, str):
                messages.append({"content": contents, "role": "user"})
            else:
                for entry in contents:
                    if isinstance(entry, str):
                        messages.append({"content": entry, "role": "user"})
                        continue

                    parts = entry.get("parts", None)
                    content = []
                    if parts is not None:
                        for part in parts:
                            if isinstance(part, str):
                                content.append(part)
                            else:
                                text = part.get("text", None)
                                if text is not None and len(text) > 0:
                                    content.append(text)

                    if len(content) > 0:
                        messages.append(
                            {
                                "content": " ".join(content),
                                "role": entry.get("role", "user"),
                            }
                        )

        return self._exclude_injected_messages(messages, payload)

    def get_formatted_response(self, payload):
        try:
            payload["conversation"]["response"]
        except KeyError:
            return []

        response = []
        if not isinstance(payload["conversation"]["response"], list):
            try:
                candidates = payload["conversation"]["response"].get("candidates", None)
            except KeyError:
                return []

            if candidates is not None:
                # Unstreamed
                # [
                #   {
                #       "content": {
                #           "parts": [
                #               {
                #                   "text": "..."
                #               }
                #           ],
                #           "role": "model"
                #       }
                #   }
                # ]
                for candidate in candidates:
                    content = candidate.get("content", None)
                    if content is not None:
                        parts = content.get("parts", None)
                        if parts is not None:
                            text = []
                            for part in parts:
                                text_content = part.get("text", None)
                                if text_content is not None:
                                    text.append(text_content)

                            if len(text) > 0:
                                response.append(
                                    {
                                        "role": content["role"],
                                        "text": "".join(text),
                                        "type": "text",
                                    }
                                )
        elif (
            len(payload["conversation"]["response"]) > 0
            and "candidates" in payload["conversation"]["response"][0]
        ):
            # Streamed
            # [
            #     {
            #         "candidates": [
            #             {
            #                 "content": {
            #                     "parts": [
            #                         {
            #                             "text": "..."
            #                         }
            #                     ],
            #                     "role": "model"
            #                 }
            #             }
            #         ]
            #     }
            # ]
            text = []
            role = None
            for entry in payload["conversation"]["response"]:
                candidates = entry.get("candidates", None)
                if candidates is not None:
                    for candidate in candidates:
                        content = candidate.get("content", None)
                        if content is not None:
                            parts = content.get("parts", None)
                            if parts is not None:
                                for part in parts:
                                    text_content = part.get("text", None)
                                    if (
                                        text_content is not None
                                        and len(text_content) > 0
                                    ):
                                        text.append(text_content)

                            if role is None:
                                role = content.get("role", None)

            if len(text) > 0:
                response.append({"role": role, "text": "".join(text), "type": "text"})

        return response
