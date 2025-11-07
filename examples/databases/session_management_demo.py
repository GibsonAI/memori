from openai import OpenAI

from memori import Memori
from memori.integrations.openai_integration import set_active_memori_context

# Initialize OpenAI client
openai_client = OpenAI()

print("=" * 70)
print("Memori Session Management Demo - Session Tracking")
print("=" * 70)
print()
print("This demo demonstrates session-based conversation tracking for a user.")
print("Sessions allow grouping related conversations while maintaining user")
print("identity. Use cases: topic-based chats, project sessions, time-based")
print("conversation grouping.")
print()
print("Features demonstrated:")
print("  - Multiple sessions for the same user")
print("  - Session-specific memory isolation")
print("  - Cross-session memory retrieval")
print("  - Session history and statistics")
print()
print("=" * 70)
print()

# Create multiple sessions for the same user
# Each session represents a different conversation context
sessions = {
    "work": Memori(
        database_connect="sqlite:///session_demo.db",
        user_id="sarah_jones",  # Same user across all sessions
        session_id="work_project_2024",  # Session for work-related conversations
        conscious_ingest=True,
        auto_ingest=True,
    ),
    "personal": Memori(
        database_connect="sqlite:///session_demo.db",
        user_id="sarah_jones",  # Same user
        session_id="personal_chat_2024",  # Session for personal conversations
        conscious_ingest=True,
        auto_ingest=True,
    ),
    "learning": Memori(
        database_connect="sqlite:///session_demo.db",
        user_id="sarah_jones",  # Same user
        session_id="learning_python_2024",  # Session for learning activities
        conscious_ingest=True,
        auto_ingest=True,
    ),
}

# Enable memory for all sessions
print("Initializing session memory systems...")
for session_name, memori in sessions.items():
    print(f"  - Enabling memory for session: {session_name}")
    memori.enable()
print()

# Demonstrate session-specific memories
print("=" * 70)
print("Phase 1: Creating Session-Specific Memories")
print("=" * 70)
print()

# Work session conversation
print("Work Session (work_project_2024):")
print("-" * 70)
work_messages = [
    "I need to finish the Q4 sales presentation by Friday.",
    "Schedule a meeting with the marketing team for next week.",
    "The client approved our proposal for the new software project.",
]

# Set work session context for multi-tenant isolation
set_active_memori_context(sessions["work"])

for msg in work_messages:
    print(f"User: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": msg}]
    )
    print(f"AI: {response.choices[0].message.content}")
    print()

# Personal session conversation
print("-" * 70)
print("Personal Session (personal_chat_2024):")
print("-" * 70)
personal_messages = [
    "I'm planning a vacation to Italy next summer.",
    "Need to remember to buy groceries: milk, eggs, bread.",
    "My favorite Italian restaurant is Bella Napoli downtown.",
]

# Set personal session context for multi-tenant isolation
set_active_memori_context(sessions["personal"])

for msg in personal_messages:
    print(f"User: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": msg}]
    )
    print(f"AI: {response.choices[0].message.content}")
    print()

# Learning session conversation
print("-" * 70)
print("Learning Session (learning_python_2024):")
print("-" * 70)
learning_messages = [
    "I'm learning Python data structures: lists, tuples, and dictionaries.",
    "Just completed a tutorial on list comprehensions.",
    "Next topic to study: object-oriented programming in Python.",
]

# Set learning session context for multi-tenant isolation
set_active_memori_context(sessions["learning"])

for msg in learning_messages:
    print(f"User: {msg}")
    response = openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": msg}]
    )
    print(f"AI: {response.choices[0].message.content}")
    print()

# Display session memory statistics
print("=" * 70)
print("Phase 2: Session Memory Statistics")
print("=" * 70)
print()

print("Memory Statistics per Session:")
print("-" * 70)
for session_name, memori in sessions.items():
    stats = memori.get_memory_stats()
    print(f"\n{session_name.upper()} Session:")
    print("  User ID: sarah_jones")
    print(f"  Session ID: {memori.session_id}")
    print(f"  Total memories: {stats.get('total_memories', 0)}")
    print(f"  Short-term: {stats.get('short_term_count', 0)}")
    print(f"  Long-term: {stats.get('long_term_count', 0)}")

print()
print("-" * 70)

# Demonstrate session-specific memory retrieval
print("\nSession-Specific Memory Retrieval:")
print("-" * 70)

# Search work session for "meeting"
print("\nSearching WORK session for 'meeting':")
work_results = sessions["work"].search("meeting", limit=3)
print(f"Found {len(work_results)} results in work session")
for i, memory in enumerate(work_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:80]}...")

# Search personal session for "meeting" (should find nothing)
print("\nSearching PERSONAL session for 'meeting':")
personal_results = sessions["personal"].search("meeting", limit=3)
print(f"Found {len(personal_results)} results in personal session")
if personal_results:
    for i, memory in enumerate(personal_results[:2], 1):
        content = memory.get("content", memory.get("searchable_content", "N/A"))
        print(f"  {i}. {content[:80]}...")
else:
    print("  No meeting-related memories in personal session!")

# Search personal session for "vacation"
print("\nSearching PERSONAL session for 'vacation':")
vacation_results = sessions["personal"].search("vacation", limit=3)
print(f"Found {len(vacation_results)} results in personal session")
for i, memory in enumerate(vacation_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:80]}...")

# Search learning session for "Python"
print("\nSearching LEARNING session for 'Python':")
python_results = sessions["learning"].search("Python", limit=3)
print(f"Found {len(python_results)} results in learning session")
for i, memory in enumerate(python_results[:2], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:80]}...")

# Create a cross-session memory instance (session_id=None retrieves from all sessions)
print()
print("-" * 70)
print("\nCross-Session Memory Retrieval (session_id=None):")
print("-" * 70)
print("Creating a Memori instance that can search across all sessions...")

all_sessions = Memori(
    database_connect="sqlite:///session_demo.db",
    user_id="sarah_jones",  # Same user
    session_id=None,  # None = search across ALL sessions for this user
    conscious_ingest=True,
    auto_ingest=True,
)
all_sessions.enable()

# Search across all sessions
print("\nSearching ALL sessions for 'Python':")
all_python_results = all_sessions.search("Python", limit=5)
print(f"Found {len(all_python_results)} results across all sessions")
for i, memory in enumerate(all_python_results[:3], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:80]}...")

print("\nSearching ALL sessions for 'project':")
all_project_results = all_sessions.search("project", limit=5)
print(f"Found {len(all_project_results)} results across all sessions")
for i, memory in enumerate(all_project_results[:3], 1):
    content = memory.get("content", memory.get("searchable_content", "N/A"))
    print(f"  {i}. {content[:80]}...")

print()
print("=" * 70)
print("Phase 3: Interactive Session-Based Chat")
print("=" * 70)
print()
print("Chat in different sessions. Type:")
print("  'work: <message>' for work session")
print("  'personal: <message>' for personal session")
print("  'learning: <message>' for learning session")
print("  'stats' to see session statistics")
print("  'switch <session>' to change active session")
print("  'exit' to quit")
print("-" * 70)

# Track current session
current_session = "work"

# Interactive loop
while True:
    try:
        user_input = input(f"\n[{current_session.upper()}] You: ").strip()

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("\nGoodbye!")
            break

        if user_input.lower() == "stats":
            print("\nSession Statistics:")
            print("-" * 70)
            for session_name, memori in sessions.items():
                stats = memori.get_memory_stats()
                print(f"\n{session_name.upper()}:")
                print(f"  Session ID: {memori.session_id}")
                print(f"  Total: {stats.get('total_memories', 0)}")
                print(f"  Short-term: {stats.get('short_term_count', 0)}")
                print(f"  Long-term: {stats.get('long_term_count', 0)}")
            continue

        if user_input.lower().startswith("switch "):
            new_session = user_input[7:].strip().lower()
            if new_session in sessions:
                current_session = new_session
                print(f"Switched to {current_session.upper()} session")
            else:
                print(f"Unknown session. Available: {', '.join(sessions.keys())}")
            continue

        # Parse session selection from message
        message = None
        selected_session = current_session

        for session_name in sessions.keys():
            if user_input.lower().startswith(f"{session_name}:"):
                selected_session = session_name
                message = user_input[len(session_name) + 1 :].strip()
                break

        if message is None:
            message = user_input

        if not message:
            print("Please provide a message")
            continue

        # Set the active context for the selected session
        set_active_memori_context(sessions[selected_session])

        print(f"Processing in {selected_session.upper()} session...")
        response = openai_client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": message}]
        )
        print(f"AI: {response.choices[0].message.content}")

    except (EOFError, KeyboardInterrupt):
        print("\nExiting...")
        break
    except Exception as e:
        print(f"Error: {e}")
        continue

print()
print("=" * 70)
print("Demo Complete!")
print("=" * 70)
print()
print("Key Takeaways:")
print("  1. Sessions group conversations within a user's context")
print("  2. Each session_id creates isolated conversation history")
print("  3. Same user_id + different session_id = separate sessions")
print("  4. session_id=None retrieves memories across ALL user sessions")
print("  5. Use sessions for: topics, projects, time periods, contexts")
print()
