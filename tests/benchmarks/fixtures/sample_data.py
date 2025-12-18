"""Helper functions for generating sample test data for benchmarks."""

import random
import string

random.seed(42)


def generate_random_string(length: int = 10) -> str:
    """Generate a random string of specified length."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_sample_fact() -> str:
    """Generate a realistic sample fact for testing."""
    templates = [
        "User likes {item}",
        "User lives in {location}",
        "User works at {company}",
        "User's favorite color is {color}",
        "User prefers {preference}",
        "User has {count} {item}",
        "User enjoys {activity}",
        "User's birthday is {date}",
    ]

    items = ["pizza", "coffee", "books", "music", "movies", "travel", "coding"]
    locations = ["New York", "San Francisco", "London", "Tokyo", "Paris"]
    companies = ["Tech Corp", "Startup Inc", "Big Company", "Small Business"]
    colors = ["blue", "red", "green", "purple", "yellow"]
    preferences = ["dark mode", "light mode", "minimalist design", "detailed UI"]
    activities = ["reading", "hiking", "cooking", "gaming", "photography"]
    dates = ["January 1st", "March 15th", "June 30th", "December 25th"]

    template = random.choice(templates)
    fact = template.format(
        item=random.choice(items),
        location=random.choice(locations),
        company=random.choice(companies),
        color=random.choice(colors),
        preference=random.choice(preferences),
        count=random.randint(1, 10),
        activity=random.choice(activities),
        date=random.choice(dates),
    )

    return fact


def generate_sample_queries() -> dict[str, list[str]]:
    """Generate sample queries of varying lengths for benchmarking."""
    return {
        "short": [
            "What do I like?",
            "Where do I live?",
            "My preferences?",
            "Favorite color?",
            "Birthday?",
        ],
        "medium": [
            "What are my favorite things?",
            "Tell me about where I live",
            "What are my preferences for software?",
            "What is my favorite color and why?",
            "When is my birthday and how do I celebrate?",
        ],
        "long": [
            "Can you tell me about all the things I like and enjoy doing?",
            "I want to know more about where I currently live and work",
            "What are all my preferences when it comes to software and design?",
            "Please provide details about my favorite color and any related memories",
            "I'd like to know when my birthday is and how I typically celebrate it",
        ],
    }


def generate_facts(count: int) -> list[str]:
    """Generate a list of unique sample facts."""
    facts = []
    seen = set()

    while len(facts) < count:
        fact = generate_sample_fact()
        # Add unique identifier to ensure no duplicates
        unique_fact = f"{fact} (id: {len(facts)})"

        # Double-check uniqueness (shouldn't be needed with id, but safe)
        if unique_fact not in seen:
            facts.append(unique_fact)
            seen.add(unique_fact)

    return facts


def generate_facts_with_size(count: int, size: str = "small") -> list[str]:
    """Generate facts for benchmarking.

    Args:
        count: Number of facts to generate
        size: Content size

    Returns:
        List of unique facts
    """
    base_facts = generate_facts(count)

    def with_id_suffix(text: str, idx: int, max_len: int) -> str:
        suffix = f" (id: {idx})"
        if max_len <= len(suffix):
            return suffix[-max_len:]
        return text[: max_len - len(suffix)] + suffix

    return [with_id_suffix(fact, i, 60) for i, fact in enumerate(base_facts)]
