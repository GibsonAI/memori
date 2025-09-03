"""
FastAPI Multi-User Memori Application
Demonstration of how to integrate Memori in a FastAPI application with multiple users

Required installations:
pip install fastapi uvicorn python-dotenv litellm memori-sdk

Run the application:
uvicorn fastapi_multiuser_app:app --reload --host 0.0.0.0 --port 8000

Then visit:
- http://localhost:8000/docs for Swagger UI
- http://localhost:8000/redoc for ReDoc
"""

from datetime import datetime
from typing import Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from litellm import completion
from pydantic import BaseModel

from memori import Memori

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Multi-User Memori API",
    description="A FastAPI application demonstrating multi-user memory isolation using Memori",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Shared database for all users
WEB_DATABASE_PATH = "sqlite:///fastapi_multiuser_memory.db"

# Global storage for user memory instances
user_memories: Dict[str, Memori] = {}
user_sessions: Dict[str, dict] = {}


# Pydantic models for request/response
class ChatMessage(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    success: bool
    response: str
    user_id: str
    namespace: str
    timestamp: str


class UserInfo(BaseModel):
    user_id: str
    namespace: str
    database: str
    created_at: str
    last_active: str
    message_count: int
    has_memory: bool


class HealthResponse(BaseModel):
    status: str
    active_users: int
    timestamp: str


class UsersResponse(BaseModel):
    users: List[str]
    total_users: int


def get_or_create_user_memory(user_id: str) -> Memori:
    """Get existing or create new Memori instance for user using shared database"""
    if user_id not in user_memories:
        print(f"👤 Creating new memory for user: {user_id}")

        user_memory = Memori(
            database_connect=WEB_DATABASE_PATH,
            namespace=f"fastapi_user_{user_id}",
            conscious_ingest=True,
        )

        user_memory.enable()
        user_memories[user_id] = user_memory

        # Track user session info
        user_sessions[user_id] = {
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "message_count": 0,
            "namespace": f"fastapi_user_{user_id}",
        }

        # Store initial user session info
        session_message = {
            "role": "system",
            "content": f"""New user session started for {user_id} at {datetime.now().isoformat()}.
            
This is a FastAPI-based chat session. The user will interact through API endpoints.
User namespace: fastapi_user_{user_id}
Database: {WEB_DATABASE_PATH}

Remember this user's preferences and conversation history within their isolated namespace.
""",
        }

        completion(model="gpt-4o-mini", messages=[session_message])

    return user_memories[user_id]


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with information about the API"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Multi-User Memori FastAPI</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .header { text-align: center; color: #2196F3; }
            .section { margin: 20px 0; padding: 15px; border-left: 4px solid #2196F3; background: #f5f5f5; }
            .endpoint { background: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 5px; }
            a { color: #2196F3; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1 class="header">🧠 Multi-User Memori FastAPI</h1>
        
        <div class="section">
            <h2>🚀 Interactive API Documentation</h2>
            <p>Use the interactive Swagger UI to test the API:</p>
            <div class="endpoint">
                📖 <a href="/docs" target="_blank"><strong>Swagger UI</strong></a> - Interactive API documentation
            </div>
            <div class="endpoint">
                📚 <a href="/redoc" target="_blank"><strong>ReDoc</strong></a> - Alternative API documentation
            </div>
        </div>
        
        <div class="section">
            <h2>🔗 Available Endpoints</h2>
            <div class="endpoint"><strong>POST /chat</strong> - Send a chat message for a specific user</div>
            <div class="endpoint"><strong>GET /users</strong> - List all active users</div>
            <div class="endpoint"><strong>GET /user/{user_id}/info</strong> - Get information about a specific user</div>
            <div class="endpoint"><strong>GET /health</strong> - Health check endpoint</div>
        </div>
        
        <div class="section">
            <h2>💡 How to Test</h2>
            <ol>
                <li>Visit <a href="/docs">/docs</a> for the interactive Swagger UI</li>
                <li>Try the <strong>POST /chat</strong> endpoint with different user_ids (e.g., "alice", "bob", "carol")</li>
                <li>Each user gets their own isolated memory namespace</li>
                <li>Check <strong>GET /users</strong> to see active users</li>
                <li>Use <strong>GET /user/{user_id}/info</strong> to see user details</li>
            </ol>
        </div>
        
        <div class="section">
            <h2>🏗️ Architecture</h2>
            <p><strong>Database:</strong> fastapi_multiuser_memory.db (shared)</p>
            <p><strong>Isolation:</strong> Per-user namespaces (fastapi_user_{user_id})</p>
            <p><strong>Memory:</strong> Persistent across sessions with conscious ingestion</p>
        </div>
    </body>
    </html>
    """


@app.post("/chat", response_model=ChatResponse)
async def chat(message_data: ChatMessage):
    """
    Send a chat message for a specific user

    - **user_id**: Unique identifier for the user (e.g., "alice", "bob", "carol")
    - **message**: The chat message to send

    Each user gets their own isolated memory namespace for conversation history.
    """
    try:
        user_id = message_data.user_id
        message = message_data.message

        if not user_id or not message:
            raise HTTPException(status_code=400, detail="Missing user_id or message")

        # Get or create user memory (this ensures the user has an active memory session)
        get_or_create_user_memory(user_id)

        # Update user session info
        if user_id in user_sessions:
            user_sessions[user_id]["last_active"] = datetime.now().isoformat()
            user_sessions[user_id]["message_count"] += 1

        # Process the message with user's memory
        response = completion(
            model="gpt-4o-mini", messages=[{"role": "user", "content": message}]
        )

        answer = response.choices[0].message.content

        return ChatResponse(
            success=True,
            response=answer,
            user_id=user_id,
            namespace=f"fastapi_user_{user_id}",
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users", response_model=UsersResponse)
async def list_users():
    """
    List all users with active memories

    Returns a list of all user IDs that have active memory sessions.
    """
    return UsersResponse(
        users=list(user_memories.keys()), total_users=len(user_memories)
    )


@app.get("/user/{user_id}/info", response_model=UserInfo)
async def get_user_info(user_id: str):
    """
    Get information about a specific user's memory

    - **user_id**: The user identifier to get information for

    Returns detailed information about the user's memory session.
    """
    if user_id not in user_memories:
        raise HTTPException(status_code=404, detail="User not found")

    session_info = user_sessions.get(user_id, {})

    return UserInfo(
        user_id=user_id,
        namespace=f"fastapi_user_{user_id}",
        database=WEB_DATABASE_PATH,
        created_at=session_info.get("created_at", ""),
        last_active=session_info.get("last_active", ""),
        message_count=session_info.get("message_count", 0),
        has_memory=True,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns the current status of the application and number of active users.
    """
    return HealthResponse(
        status="healthy",
        active_users=len(user_memories),
        timestamp=datetime.now().isoformat(),
    )


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Multi-User Memori FastAPI Application")
    print("=" * 60)
    print("Features:")
    print("✅ Isolated memory per user using namespaces")
    print("✅ FastAPI with automatic OpenAPI documentation")
    print("✅ Interactive Swagger UI for testing")
    print("✅ Persistent memory across sessions")
    print("✅ RESTful API endpoints")
    print()
    print("Available endpoints:")
    print("  GET  /           - Application info")
    print("  POST /chat       - Send chat message")
    print("  GET  /users      - List active users")
    print("  GET  /user/{id}/info - User memory info")
    print("  GET  /health     - Health check")
    print()
    print("📖 Interactive Documentation:")
    print("  Swagger UI: http://localhost:8000/docs")
    print("  ReDoc:      http://localhost:8000/redoc")
    print()
    print("🧠 Database: fastapi_multiuser_memory.db")
    print("🏷️  Namespaces: fastapi_user_{user_id}")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
