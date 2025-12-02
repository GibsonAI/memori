r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class AugmentationInput:
    """Data class for augmentation input."""

    conversation_id: str | None
    entity_id: str | None
    process_id: str | None
    conversation_messages: list[dict[str, Any]]
    system_prompt: str | None = None
