import os
import sys
import asyncio
import litellm
from litellm import acompletion

# Add the root project folder to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from memori import Memori

# Turn off verbose LiteLLM logs
litellm.suppress_debug_info = True

async def main():
    # 1. Setup Database
    db_file = "streaming_test.db"
    if os.path.exists(db_file):
        os.remove(db_file)
    
    connection_string = f"sqlite:///{db_file}"
    
    print(f"--- Starting Simplified Streaming Test ---")
    
    # 2. Initialize Memori
    memory = Memori(
        database_connect=connection_string,
        verbose=True
    )
    memory.enable()
    
    # 3. Define Test Data
    user_input = "What is the capital of France?"
    mock_output = "The capital of France is Paris."
    
    print(f"User Input: {user_input}")
    print("Sending async streaming request (Mocked)...")
    
    try:
        # 4. Call LiteLLM with stream=True and mock_response
        response = await acompletion(
            model="gpt-4o", 
            messages=[{"role": "user", "content": user_input}],
            stream=True,
            mock_response=mock_output
        )
        
        # 5. Consume the stream (Required for the callback to trigger on completion)
        collected_content = ""
        print("Receiving chunks:", end=" ")
        async for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                collected_content += content
                print(".", end="", flush=True)
        print(f"\nFull response received: {collected_content}")
        
        # 6. Wait briefly for the background callback to write to DB
        print("Waiting for database write...")
        await asyncio.sleep(1)
        
        # 7. Verify DB contents
        history = memory.db_manager.get_chat_history(limit=1)
        
        if history:
            record = history[0]
            print("\n✅ SUCCESS: Conversation recorded in database!")
            print(f"   - Input stored: '{record['user_input']}'")
            print(f"   - Output stored: '{record['ai_output']}'")
            
            # Check if metadata captured the stream flag
            if record.get('metadata') and record['metadata'].get('stream'):
                print("   - Metadata correctly identified stream=True")
        else:
            print("\n❌ FAILURE: Database is empty. Streaming callback failed.")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
    
    # 8. Cleanup
    memory.disable()
    if hasattr(memory.db_manager, "close"):
        memory.db_manager.close()
    if os.path.exists(db_file):
        os.remove(db_file)

if __name__ == "__main__":
    asyncio.run(main())