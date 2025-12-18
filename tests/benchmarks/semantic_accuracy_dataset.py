"""
Curated semantic-accuracy dataset for recall evaluation.

Each query maps to one or more acceptable facts (strings) that should be returned by recall.
More relevant facts per query = finer-grained recall metrics.
"""

DATASET = {
    "facts": [
        # Location facts (0-4)
        "User lives in Paris (id: 0)",
        "User's apartment is in the 11th arrondissement (id: 1)",
        "User moved to France 3 years ago (id: 2)",
        "User previously lived in London (id: 3)",
        "User's office is near the Eiffel Tower (id: 4)",
        # Color/preference facts (5-9)
        "User's favorite color is blue (id: 5)",
        "User prefers navy blue over light blue (id: 6)",
        "User likes wearing blue shirts (id: 7)",
        "User painted their room blue (id: 8)",
        "User's car is blue (id: 9)",
        # Food facts (10-19)
        "User likes pizza (id: 10)",
        "User enjoys Italian cuisine (id: 11)",
        "User's favorite pizza topping is pepperoni (id: 12)",
        "User likes coffee (id: 13)",
        "User drinks espresso every morning (id: 14)",
        "User prefers dark roast coffee (id: 15)",
        "User enjoys sushi (id: 16)",
        "User is vegetarian on weekdays (id: 17)",
        "User loves Thai food (id: 18)",
        "User dislikes cilantro (id: 19)",
        # Work facts (20-24)
        "User works at Tech Corp (id: 20)",
        "User is a software engineer (id: 21)",
        "User has been at Tech Corp for 2 years (id: 22)",
        "User works remotely on Fridays (id: 23)",
        "User's manager is named Sarah (id: 24)",
        # Hobby facts (25-34)
        "User enjoys hiking (id: 25)",
        "User hiked Mont Blanc last summer (id: 26)",
        "User goes hiking every weekend (id: 27)",
        "User enjoys cooking (id: 28)",
        "User took a cooking class in Italy (id: 29)",
        "User specializes in French cuisine (id: 30)",
        "User plays guitar (id: 31)",
        "User reads science fiction (id: 32)",
        "User practices yoga (id: 33)",
        "User runs marathons (id: 34)",
        # Settings/preferences (35-39)
        "User prefers dark mode (id: 35)",
        "User uses vim keybindings (id: 36)",
        "User prefers metric units (id: 37)",
        "User's timezone is CET (id: 38)",
        "User speaks French and English (id: 39)",
        # Personal facts (40-49)
        "User's birthday is March 15th (id: 40)",
        "User was born in 1990 (id: 41)",
        "User is 34 years old (id: 42)",
        "User has 2 cats (id: 43)",
        "User's cats are named Luna and Shadow (id: 44)",
        "User adopted the cats in 2021 (id: 45)",
        "User is married (id: 46)",
        "User's spouse works in finance (id: 47)",
        "User has a brother named Tom (id: 48)",
        "User's mother lives in Spain (id: 49)",
    ],
    # query -> list of acceptable facts (relevant set)
    # Each query has 5-10 relevant facts for finer-grained recall
    "queries": {
        "Where do I live?": [
            "User lives in Paris (id: 0)",
            "User's apartment is in the 11th arrondissement (id: 1)",
            "User moved to France 3 years ago (id: 2)",
            "User previously lived in London (id: 3)",
            "User's office is near the Eiffel Tower (id: 4)",
            "User's timezone is CET (id: 38)",
        ],
        "What's my favorite color?": [
            "User's favorite color is blue (id: 5)",
            "User prefers navy blue over light blue (id: 6)",
            "User likes wearing blue shirts (id: 7)",
            "User painted their room blue (id: 8)",
            "User's car is blue (id: 9)",
        ],
        "What food do I like?": [
            "User likes pizza (id: 10)",
            "User enjoys Italian cuisine (id: 11)",
            "User's favorite pizza topping is pepperoni (id: 12)",
            "User likes coffee (id: 13)",
            "User enjoys sushi (id: 16)",
            "User loves Thai food (id: 18)",
        ],
        "Tell me about my coffee preferences": [
            "User likes coffee (id: 13)",
            "User drinks espresso every morning (id: 14)",
            "User prefers dark roast coffee (id: 15)",
        ],
        "Where do I work?": [
            "User works at Tech Corp (id: 20)",
            "User is a software engineer (id: 21)",
            "User has been at Tech Corp for 2 years (id: 22)",
            "User works remotely on Fridays (id: 23)",
            "User's manager is named Sarah (id: 24)",
            "User's office is near the Eiffel Tower (id: 4)",
        ],
        "What do I enjoy doing outdoors?": [
            "User enjoys hiking (id: 25)",
            "User hiked Mont Blanc last summer (id: 26)",
            "User goes hiking every weekend (id: 27)",
            "User runs marathons (id: 34)",
        ],
        "What are my cooking skills?": [
            "User enjoys cooking (id: 28)",
            "User took a cooking class in Italy (id: 29)",
            "User specializes in French cuisine (id: 30)",
        ],
        "What hobbies do I have?": [
            "User enjoys hiking (id: 25)",
            "User goes hiking every weekend (id: 27)",
            "User enjoys cooking (id: 28)",
            "User plays guitar (id: 31)",
            "User reads science fiction (id: 32)",
            "User practices yoga (id: 33)",
            "User runs marathons (id: 34)",
        ],
        "Do I prefer dark mode?": [
            "User prefers dark mode (id: 35)",
            "User uses vim keybindings (id: 36)",
        ],
        "When is my birthday?": [
            "User's birthday is March 15th (id: 40)",
            "User was born in 1990 (id: 41)",
            "User is 34 years old (id: 42)",
        ],
        "Do I have any pets?": [
            "User has 2 cats (id: 43)",
            "User's cats are named Luna and Shadow (id: 44)",
            "User adopted the cats in 2021 (id: 45)",
        ],
        "Tell me about my family": [
            "User is married (id: 46)",
            "User's spouse works in finance (id: 47)",
            "User has a brother named Tom (id: 48)",
            "User's mother lives in Spain (id: 49)",
        ],
    },
}
