"""
Small, curated semantic-accuracy dataset.

Each query maps to one or more acceptable facts (strings) that should be returned by recall.
This is the "right way": evaluate retrieval quality against a labeled dataset.
"""

DATASET = {
    "facts": [
        "User lives in Paris (id: 0)",
        "User's favorite color is blue (id: 1)",
        "User likes pizza (id: 2)",
        "User works at Tech Corp (id: 3)",
        "User enjoys hiking (id: 4)",
        "User prefers dark mode (id: 5)",
        "User's birthday is March 15th (id: 6)",
        "User has 2 cats (id: 7)",
        "User enjoys cooking (id: 8)",
        "User likes coffee (id: 9)",
    ],
    # query -> list of acceptable facts (relevant set)
    "queries": {
        "Where do I live?": ["User lives in Paris (id: 0)"],
        "What's my favorite color?": ["User's favorite color is blue (id: 1)"],
        "What food do I like?": [
            "User likes pizza (id: 2)",
            "User likes coffee (id: 9)",
        ],
        "Where do I work?": ["User works at Tech Corp (id: 3)"],
        "What do I enjoy doing?": [
            "User enjoys hiking (id: 4)",
            "User enjoys cooking (id: 8)",
        ],
        "Do I prefer dark mode?": ["User prefers dark mode (id: 5)"],
        "When is my birthday?": ["User's birthday is March 15th (id: 6)"],
        "Do I have any pets?": ["User has 2 cats (id: 7)"],
    },
}
