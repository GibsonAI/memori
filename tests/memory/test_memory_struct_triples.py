from memori.memory._struct import Entity


def test_entity_configure_with_triples_field():
    entity = Entity().configure_from_advanced_augmentation(
        {
            "entity": {
                "triples": [
                    {
                        "subject": {"name": "User", "type": "Person"},
                        "predicate": "likes",
                        "object": {"name": "Pizza", "type": "Food"},
                    }
                ]
            }
        }
    )

    assert len(entity.semantic_triples) == 1
    assert entity.semantic_triples[0].subject_name == "User"
    assert entity.semantic_triples[0].subject_type == "person"
    assert entity.semantic_triples[0].predicate == "likes"
    assert entity.semantic_triples[0].object_name == "Pizza"
    assert entity.semantic_triples[0].object_type == "food"
    assert len(entity.facts) == 1
    assert entity.facts[0] == "User likes Pizza"


def test_entity_configure_with_both_semantic_triples_and_triples():
    entity = Entity().configure_from_advanced_augmentation(
        {
            "entity": {
                "semantic_triples": [
                    {
                        "subject": {"name": "Alice", "type": "Person"},
                        "predicate": "works_at",
                        "object": {"name": "TechCorp", "type": "Organization"},
                    }
                ],
                "triples": [
                    {
                        "subject": {"name": "Bob", "type": "Person"},
                        "predicate": "lives_in",
                        "object": {"name": "NYC", "type": "City"},
                    }
                ],
            }
        }
    )

    assert len(entity.semantic_triples) == 2
    assert entity.semantic_triples[0].subject_name == "Alice"
    assert entity.semantic_triples[1].subject_name == "Bob"
    assert len(entity.facts) == 1
    assert entity.facts[0] == "Bob lives_in NYC"


def test_entity_triples_generates_fact_text():
    entity = Entity().configure_from_advanced_augmentation(
        {
            "entity": {
                "triples": [
                    {
                        "subject": {"name": "Car", "type": "Vehicle"},
                        "predicate": "has_color",
                        "object": {"name": "Red", "type": "Color"},
                    },
                    {
                        "subject": {"name": "House", "type": "Building"},
                        "predicate": "located_in",
                        "object": {"name": "Seattle", "type": "City"},
                    },
                ]
            }
        }
    )

    assert len(entity.facts) == 2
    assert "Car has_color Red" in entity.facts
    assert "House located_in Seattle" in entity.facts


def test_entity_triples_with_existing_facts():
    entity = Entity().configure_from_advanced_augmentation(
        {
            "entity": {
                "facts": ["Existing fact 1", "Existing fact 2"],
                "triples": [
                    {
                        "subject": {"name": "John", "type": "Person"},
                        "predicate": "drives",
                        "object": {"name": "Tesla", "type": "Car"},
                    }
                ],
            }
        }
    )

    assert len(entity.facts) == 3
    assert "Existing fact 1" in entity.facts
    assert "Existing fact 2" in entity.facts
    assert "John drives Tesla" in entity.facts


def test_entity_triples_with_missing_fields_skipped():
    entity = Entity().configure_from_advanced_augmentation(
        {
            "entity": {
                "triples": [
                    {
                        "subject": {"name": "Valid", "type": "Person"},
                        "predicate": "likes",
                        "object": {"name": "Coffee", "type": "Beverage"},
                    },
                    {"subject": {"name": "Invalid"}, "predicate": "missing_object"},
                    {"predicate": "no_subject_or_object"},
                ]
            }
        }
    )

    assert len(entity.semantic_triples) == 1
    assert entity.semantic_triples[0].subject_name == "Valid"
    assert len(entity.facts) == 1
    assert entity.facts[0] == "Valid likes Coffee"


def test_entity_semantic_triples_only_not_added_to_facts():
    entity = Entity().configure_from_advanced_augmentation(
        {
            "entity": {
                "semantic_triples": [
                    {
                        "subject": {"name": "Alice", "type": "Person"},
                        "predicate": "knows",
                        "object": {"name": "Bob", "type": "Person"},
                    }
                ]
            }
        }
    )

    assert len(entity.semantic_triples) == 1
    assert len(entity.facts) == 0


def test_entity_triples_empty_list():
    entity = Entity().configure_from_advanced_augmentation({"entity": {"triples": []}})

    assert len(entity.semantic_triples) == 0
    assert len(entity.facts) == 0


def test_entity_triples_type_normalization():
    entity = Entity().configure_from_advanced_augmentation(
        {
            "entity": {
                "triples": [
                    {
                        "subject": {"name": "Test", "type": "UPPERCASE"},
                        "predicate": "test_predicate",
                        "object": {"name": "Object", "type": "MiXeDCaSe"},
                    }
                ]
            }
        }
    )

    assert entity.semantic_triples[0].subject_type == "uppercase"
    assert entity.semantic_triples[0].object_type == "mixedcase"
