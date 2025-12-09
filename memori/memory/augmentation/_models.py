r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                 perfectam memoriam
                      memorilabs.ai
"""

import hashlib
from dataclasses import dataclass, field


def hash_id(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass
class ConversationData:
    """Conversation data structure for augmentation payload."""

    messages: list
    summary: str | None = None


@dataclass
class SdkVersionData:
    """SDK version data structure."""

    version: str | None = None


@dataclass
class ModelData:
    """Model metadata structure."""

    provider: str | None = None
    sdk: SdkVersionData = field(default_factory=SdkVersionData)
    version: str | None = None


@dataclass
class FrameworkData:
    """Framework metadata structure."""

    provider: str | None = None


@dataclass
class LlmData:
    """LLM metadata structure."""

    model: ModelData = field(default_factory=ModelData)


@dataclass
class PlatformData:
    """Platform metadata structure."""

    provider: str | None = None


@dataclass
class SdkData:
    """SDK metadata structure."""

    lang: str = "python"
    version: str | None = None


@dataclass
class StorageData:
    """Storage metadata structure."""

    cockroachdb: bool = False
    dialect: str | None = None


@dataclass
class EntityData:
    """Entity metadata structure."""

    id: str | None = None


@dataclass
class ProcessData:
    """Process metadata structure."""

    id: str | None = None


@dataclass
class AttributionData:
    """Attribution metadata structure."""

    entity: EntityData = field(default_factory=EntityData)
    process: ProcessData = field(default_factory=ProcessData)


@dataclass
class MetaData:
    """Meta information structure for augmentation payload."""

    framework: FrameworkData = field(default_factory=FrameworkData)
    llm: LlmData = field(default_factory=LlmData)
    platform: PlatformData = field(default_factory=PlatformData)
    sdk: SdkData = field(default_factory=SdkData)
    storage: StorageData = field(default_factory=StorageData)
    attribution: AttributionData = field(default_factory=AttributionData)


@dataclass
class AugmentationPayload:
    """Complete augmentation API payload structure."""

    conversation: ConversationData
    meta: MetaData

    def to_dict(self) -> dict:
        """Convert the dataclass to a dictionary for API submission."""
        return {
            "conversation": {
                "messages": self.conversation.messages,
                "summary": self.conversation.summary,
            },
            "meta": {
                "attribution": {
                    "entity": {
                        "id": self.meta.attribution.entity.id,
                    },
                    "process": {
                        "id": self.meta.attribution.process.id,
                    },
                },
                "framework": {
                    "provider": self.meta.framework.provider,
                },
                "llm": {
                    "model": {
                        "provider": self.meta.llm.model.provider,
                        "sdk": {
                            "version": self.meta.llm.model.sdk.version,
                        },
                        "version": self.meta.llm.model.version,
                    }
                },
                "platform": {
                    "provider": self.meta.platform.provider,
                },
                "sdk": {
                    "lang": self.meta.sdk.lang,
                    "version": self.meta.sdk.version,
                },
                "storage": {
                    "cockroachdb": self.meta.storage.cockroachdb,
                    "dialect": self.meta.storage.dialect,
                },
            },
        }
