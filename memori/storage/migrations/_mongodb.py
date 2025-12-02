r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

migrations = {
    1: [
        {
            "description": "create collection memori_schema_version",
            "operations": [
                {
                    "collection": "memori_schema_version",
                    "method": "create_index",
                    "args": [[("num", 1)]],
                    "kwargs": {"unique": True},
                },
            ],
        },
        {
            "description": "create collection memori_entity",
            "operations": [
                {
                    "collection": "memori_entity",
                    "method": "create_index",
                    "args": [[("external_id", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_entity",
                    "method": "create_index",
                    "args": [[("uuid", 1)]],
                    "kwargs": {"unique": True},
                },
            ],
        },
        {
            "description": "create collection memori_process",
            "operations": [
                {
                    "collection": "memori_process",
                    "method": "create_index",
                    "args": [[("external_id", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_process",
                    "method": "create_index",
                    "args": [[("uuid", 1)]],
                    "kwargs": {"unique": True},
                },
            ],
        },
        {
            "description": "create collection memori_session",
            "operations": [
                {
                    "collection": "memori_session",
                    "method": "create_index",
                    "args": [[("uuid", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_session",
                    "method": "create_index",
                    "args": [[("entity_id", 1), ("_id", 1)]],
                    "kwargs": {"unique": True, "sparse": True},
                },
                {
                    "collection": "memori_session",
                    "method": "create_index",
                    "args": [[("process_id", 1), ("_id", 1)]],
                    "kwargs": {"unique": True, "sparse": True},
                },
            ],
        },
        {
            "description": "create collection memori_conversation",
            "operations": [
                {
                    "collection": "memori_conversation",
                    "method": "create_index",
                    "args": [[("session_id", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_conversation",
                    "method": "create_index",
                    "args": [[("uuid", 1)]],
                    "kwargs": {"unique": True},
                },
            ],
        },
        {
            "description": "create collection memori_conversation_message",
            "operations": [
                {
                    "collection": "memori_conversation_message",
                    "method": "create_index",
                    "args": [[("uuid", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_conversation_message",
                    "method": "create_index",
                    "args": [[("conversation_id", 1), ("_id", 1)]],
                    "kwargs": {"unique": True},
                },
            ],
        },
        {
            "description": "create collection memori_entity_fact",
            "operations": [
                {
                    "collection": "memori_entity_fact",
                    "method": "create_index",
                    "args": [[("uuid", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_entity_fact",
                    "method": "create_index",
                    "args": [[("entity_id", 1), ("_id", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_entity_fact",
                    "method": "create_index",
                    "args": [[("entity_id", 1), ("uniq", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_entity_fact",
                    "method": "create_index",
                    "args": [
                        [("entity_id", 1), ("num_times", -1), ("date_last_time", -1)]
                    ],
                    "kwargs": {"name": "idx_memori_entity_fact_entity_id_freq"},
                },
                {
                    "collection": "memori_entity_fact",
                    "method": "create_index",
                    "args": [[("entity_id", 1), ("_id", 1)]],
                    "kwargs": {"name": "idx_memori_entity_fact_embedding_search"},
                },
            ],
        },
        {
            "description": "create collection memori_process_attribute",
            "operations": [
                {
                    "collection": "memori_process_attribute",
                    "method": "create_index",
                    "args": [[("uuid", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_process_attribute",
                    "method": "create_index",
                    "args": [[("process_id", 1), ("_id", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_process_attribute",
                    "method": "create_index",
                    "args": [[("process_id", 1), ("uniq", 1)]],
                    "kwargs": {"unique": True},
                },
            ],
        },
        {
            "description": "create collection memori_subject",
            "operations": [
                {
                    "collection": "memori_subject",
                    "method": "create_index",
                    "args": [[("uuid", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_subject",
                    "method": "create_index",
                    "args": [[("uniq", 1)]],
                    "kwargs": {"unique": True},
                },
            ],
        },
        {
            "description": "create collection memori_predicate",
            "operations": [
                {
                    "collection": "memori_predicate",
                    "method": "create_index",
                    "args": [[("uuid", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_predicate",
                    "method": "create_index",
                    "args": [[("uniq", 1)]],
                    "kwargs": {"unique": True},
                },
            ],
        },
        {
            "description": "create collection memori_object",
            "operations": [
                {
                    "collection": "memori_object",
                    "method": "create_index",
                    "args": [[("uuid", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_object",
                    "method": "create_index",
                    "args": [[("uniq", 1)]],
                    "kwargs": {"unique": True},
                },
            ],
        },
        {
            "description": "create collection memori_knowledge_graph",
            "operations": [
                {
                    "collection": "memori_knowledge_graph",
                    "method": "create_index",
                    "args": [[("uuid", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_knowledge_graph",
                    "method": "create_index",
                    "args": [[("entity_id", 1), ("_id", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_knowledge_graph",
                    "method": "create_index",
                    "args": [
                        [
                            ("entity_id", 1),
                            ("subject_id", 1),
                            ("predicate_id", 1),
                            ("object_id", 1),
                        ]
                    ],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_knowledge_graph",
                    "method": "create_index",
                    "args": [[("subject_id", 1), ("_id", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_knowledge_graph",
                    "method": "create_index",
                    "args": [[("predicate_id", 1), ("_id", 1)]],
                    "kwargs": {"unique": True},
                },
                {
                    "collection": "memori_knowledge_graph",
                    "method": "create_index",
                    "args": [[("object_id", 1), ("_id", 1)]],
                    "kwargs": {"unique": True},
                },
            ],
        },
    ]
}
