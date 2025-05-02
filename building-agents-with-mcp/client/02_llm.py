import asyncio
import os

from dotenv import load_dotenv
from openai import OpenAI, BadRequestError
from utils.client_manager import ClientManager

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

model = os.getenv("MODEL")

# Debug environment variables
print("All environment variables:")
for key, value in os.environ.items():
    if key.startswith("OPENAI") or key == "MODEL":
        # Mask the API key for security
        if key == "OPENAI_API_KEY" and value:
            masked_value = value[:10] + "..." + value[-5:]
            print(f"{key}: {masked_value}")
        else:
            print(f"{key}: {value}")


async def main():
    client_manager = ClientManager()
    client_manager.load_servers("servers.yaml")

    await client_manager.connect_to_server()

    # Create a chat completion
    # Assuming ChatCompletionToolParam is a class
    # print("OpenAI tools: ", client.tools)
    # print("MCP tools: ", client_manager.tools)
    print("OpenAI model: ", os.getenv("MODEL"))
    print("OpenAI API key: ", os.getenv("OPENAI_API_KEY")[:10] + "..." + os.getenv("OPENAI_API_KEY")[-5:] if os.getenv("OPENAI_API_KEY") else None)
    query = input("Enter a query: ")
    
    try:
        print("Sending request to OpenAI with model:", model)
        # Let's check if model is None
        if model is None:
            print("WARNING: MODEL environment variable is not set. Using a default model.")
            model_to_use = "gpt-4o"
        else:
            model_to_use = model
            
        print("Using model:", model_to_use)
        response = client.chat.completions.create(
            model=model_to_use,
            messages=[{"role": "user", "content": f"User's query: {query}"}],
            tools=client_manager.tools,
            tool_choice="auto",
            temperature=0.0,
        )
        
        print("OpenAI response received:", response)
        print("Tool calls:", response.choices[0].message.tool_calls)

        if response.choices[0].message.tool_calls:
            results = await client_manager.process_tool_call(
                response.choices[0].message.tool_calls
            )
            print(results[0])
        else:
            print("No tool calls in the response")
            print("Response content:", response.choices[0].message.content)
    except BadRequestError as e:
        print(f"OpenAI API Error: {e}")
    except Exception as e:
        print(f"Other error: {e}")
        import traceback
        traceback.print_exc()

    await client_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
