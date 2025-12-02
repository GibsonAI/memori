r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""


class Conversation:
    def __init__(self):
        self.summary: str | None = None

    def configure_from_advanced_augmentation(self, json_: dict) -> "Conversation":
        conversation = json_.get("conversation", None)
        if conversation is None:
            return self

        self.summary = conversation.get("summary", None)

        return self


class Entity:
    def __init__(self):
        self.facts: list[str] = []
        self.fact_embeddings: list[list[float]] = []
        self.semantic_triples: list[SemanticTriple] = []

    def configure_from_advanced_augmentation(self, json_: dict) -> "Entity":
        entity = json_.get("entity", None)
        if entity is None:
            return self

        self.facts.extend(entity.get("facts", []))
        self.fact_embeddings.extend(entity.get("fact_embeddings", []))

        semantic_triples = entity.get("semantic_triples", [])
        triples = entity.get("triples", [])

        for entry in semantic_triples:
            triple = self._parse_semantic_triple(entry)
            if triple is not None:
                self.semantic_triples.append(triple)

        for entry in triples:
            triple = self._parse_semantic_triple(entry)
            if triple is not None:
                self.semantic_triples.append(triple)
                fact_text = (
                    f"{triple.subject_name} {triple.predicate} {triple.object_name}"
                )
                self.facts.append(fact_text)

        return self

    def _parse_semantic_triple(self, entry: dict) -> "SemanticTriple | None":
        """Parse a semantic triple from API response."""
        subject = entry.get("subject")
        predicate = entry.get("predicate")
        object_ = entry.get("object")

        if not subject or not predicate or not object_:
            return None

        subject_name = subject.get("name")
        subject_type = subject.get("type")
        object_name = object_.get("name")
        object_type = object_.get("type")

        if not all([subject_name, subject_type, object_name, object_type]):
            return None

        triple = SemanticTriple()
        triple.subject_name = subject_name
        triple.subject_type = subject_type.lower()
        triple.predicate = predicate
        triple.object_name = object_name
        triple.object_type = object_type.lower()

        return triple


class Memories:
    def __init__(self):
        self.conversation: Conversation = Conversation()
        self.entity: Entity = Entity()
        self.process: Process = Process()

    def configure_from_advanced_augmentation(self, json_: dict) -> "Memories":
        self.conversation = Conversation().configure_from_advanced_augmentation(json_)
        self.entity = Entity().configure_from_advanced_augmentation(json_)
        self.process = Process().configure_from_advanced_augmentation(json_)
        return self


class Process:
    def __init__(self):
        self.attributes: list[str] = []

    def configure_from_advanced_augmentation(self, json_: dict) -> "Process":
        process = json_.get("process", None)
        if process is None:
            return self

        self.attributes.extend(process.get("attributes", []))

        return self


class SemanticTriple:
    def __init__(self):
        self.subject_name: str | None = None
        self.subject_type: str | None = None
        self.predicate: str | None = None
        self.object_name: str | None = None
        self.object_type: str | None = None
