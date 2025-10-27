import asyncio
import os

import dotenv

from memori import Memori
from openai import AsyncOpenAI

# Load environment variables from .env file
dotenv.load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
model = os.getenv("OPENAI_MODEL", "gpt-4")

client = AsyncOpenAI(api_key=api_key, base_url=base_url)

print("Initializing Memori with OpenAI...")
openai_memory = Memori(
    database_connect="sqlite:///openai_custom_demo.db",
    conscious_ingest=True,
    auto_ingest=True,
    verbose=True,
    api_key=api_key,
    base_url=base_url,
    model=model,
)

print("Enabling memory tracking...")
openai_memory.enable()

print(f"Memori OpenAI Example - Chat with {model} while memory is being tracked")
print("Type 'exit' or press Ctrl+C to quit")
print("-" * 50)

use_stream = True


async def main():
    while True:
        user_input = input("User: ")
        if not user_input.strip():
            continue

        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        print("Processing your message with memory tracking...")

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": user_input}],
            stream=use_stream,
        )

        if use_stream:
            full_response = ""
            async for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    print(content, end="", flush=True)  # 实时显示
            print()  # 换行
            # async def finalize_callback(final_response, _context):
            #     print(chunks)
            #     """Callback to record conversation when streaming completes."""
            #     if final_response is not None:
            #         print(f"AI: {final_response.choices[0].message.content}")
            #         print()  # Add blank line for readability

            # create_openai_streaming_proxy(
            #     stream=response,
            #     finalize_callback=finalize_callback
            # )
        else:
            print(f"AI: {response.choices[0].message.content}")
            print()  # Add blank line for readability


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (EOFError, KeyboardInterrupt):
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
