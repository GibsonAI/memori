from memori.memory._struct import Conversation, Entity, Memories, Process


def test_conversation_configure_from_advanced_augmentation():
    conversation = Conversation().configure_from_advanced_augmentation({})
    assert conversation.summary is None

    conversation = Conversation().configure_from_advanced_augmentation(
        {"conversation": {}}
    )
    assert conversation.summary is None

    conversation = Conversation().configure_from_advanced_augmentation(
        {"conversation": {"summary": "Abc def"}}
    )
    assert conversation.summary == "Abc def"


def test_entity_configure_from_advanced_augmentation():
    entity = Entity().configure_from_advanced_augmentation({})
    assert entity.facts == []
    assert entity.semantic_triples == []

    entity = Entity().configure_from_advanced_augmentation({"entity": {}})
    assert entity.facts == []
    assert entity.semantic_triples == []

    entity = Entity().configure_from_advanced_augmentation(
        {
            "entity": {
                "facts": ["Abc def", "ghi", "jkl"],
                "semantic_triples": [
                    {
                        "subject": {"name": "Mno", "type": "Pqr"},
                        "predicate": "stu",
                        "object": {"name": "vwx", "type": "Yza"},
                    }
                ],
            }
        }
    )
    assert entity.facts == ["Abc def", "ghi", "jkl"]
    assert len(entity.semantic_triples) == 1
    assert entity.semantic_triples[0].subject_name == "Mno"
    assert entity.semantic_triples[0].subject_type == "pqr"
    assert entity.semantic_triples[0].predicate == "stu"
    assert entity.semantic_triples[0].object_name == "vwx"
    assert entity.semantic_triples[0].object_type == "yza"


def test_process_configure_from_advanced_augmentation():
    process = Process().configure_from_advanced_augmentation({})
    assert process.attributes == []

    process = Process().configure_from_advanced_augmentation({"process": {}})
    assert process.attributes == []

    process = Process().configure_from_advanced_augmentation(
        {"process": {"attributes": ["Abc", "def"]}}
    )
    assert process.attributes == ["Abc", "def"]


def test_memories_configure_from_advanced_augmentation():
    memories = Memories().configure_from_advanced_augmentation(
        {
            "conversation": {"summary": "Abc def"},
            "entity": {
                "facts": ["Abc def", "ghi", "jkl"],
                "semantic_triples": [
                    {
                        "subject": {"name": "Mno", "type": "Pqr"},
                        "predicate": "stu",
                        "object": {"name": "vwx", "type": "Yza"},
                    }
                ],
            },
            "process": {"attributes": ["Abc", "def"]},
        }
    )

    assert memories.conversation.summary == "Abc def"
    assert memories.entity.facts == ["Abc def", "ghi", "jkl"]
    assert len(memories.entity.semantic_triples) == 1
    assert memories.entity.semantic_triples[0].subject_name == "Mno"
    assert memories.entity.semantic_triples[0].subject_type == "pqr"
    assert memories.entity.semantic_triples[0].predicate == "stu"
    assert memories.entity.semantic_triples[0].object_name == "vwx"
    assert memories.entity.semantic_triples[0].object_type == "yza"
    assert memories.process.attributes == ["Abc", "def"]
