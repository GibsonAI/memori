r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from memori.llm import _clients  # noqa: F401
from memori.llm._registry import Registry
from memori.llm.adapters import anthropic, bedrock, google, openai, xai  # noqa: F401

__all__ = ["Registry"]
