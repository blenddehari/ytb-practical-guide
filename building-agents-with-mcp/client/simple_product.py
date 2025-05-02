import asyncio
import os
import json
import httpx

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

model = os.getenv('MODEL', 'gpt-4o')

# Server configuration from servers.yaml
PRODUCT_SERVER_URL = "http://localhost:8001/sse"
PRODUCT_API_KEY = "secret-key3"

# Define the tool schema manually
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_product",
            "description": "Create a new product with a ticket",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the product"
                    },
                    "short_description": {
                        "type": "string",
                        "description": "Short description of the product"
                    },
                    "long_description": {
                        "type": "string",
                        "description": "Long description of the product"
                    },
                    "ticket_price": {
                        "type": "number",
                        "description": "Price of the ticket"
                    },
                    "ticket_type": {
                        "type": "string",
                        "description": "Type of ticket (e.g., Adult, Child, Senior)"
                    },
                    "ticket_category": {
                        "type": "string",
                        "description": "Category of ticket (e.g., 1 Day, 2 Day, Weekend)"
                    }
                },
                "required": ["title", "short_description", "long_description", "ticket_price", "ticket_type", "ticket_category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_products",
            "description": "List all existing products",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

async def call_product_tool(tool_name, tool_args):
    """Call a tool on the product server"""
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            PRODUCT_SERVER_URL,
            json={
                "type": "call_tool",
                "id": f"call-{tool_name}-{os.urandom(4).hex()}", 
                "name": tool_name,
                "input": tool_args
            },
            headers={"Authorization": f"Bearer {PRODUCT_API_KEY}"}
        )
        
        if response.status_code != 200:
            return {"error": f"Server returned status code {response.status_code}"}
        
        return response.json()

async def main():
    print('\n=== Product Creation Assistant ===')
    print('This assistant will help you create and list products using the following tools:')
    for tool in tools:
        print(f'- {tool["function"]["name"]}: {tool["function"]["description"]}')
        if tool["function"]["name"] == "create_product":
            print('  Required information:')
            for param, details in tool["function"]["parameters"]["properties"].items():
                required = '(required)' if param in tool["function"]["parameters"].get('required', []) else '(optional)'
                print(f'    - {param}: {details["description"]} {required}')

    print('\nYou can start by describing what you want to do.')
    print('Examples:')
    print('  - "Create a concert ticket for the Summer Festival"')
    print('  - "List all existing products"')
    print('\nType "exit", "quit", or "bye" to end the conversation.')
    
    # Start conversation
    messages = []
    
    # Continue conversation until user explicitly quits
    while True:
        query = input('\n> ')
        
        # Check if user wants to quit
        if query.lower() in ['exit', 'quit', 'bye', 'q', 'end']:
            print('\nThank you for using the Product Creation Assistant. Goodbye!')
            break
        
        # Add user message to the conversation
        messages.append({'role': 'user', 'content': query})
        
        try:
            print('\nProcessing your request...')
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice='auto',
                temperature=0.0,
            )
            
            # Get the assistant's message
            assistant_message = response.choices[0].message
            messages.append(assistant_message.model_dump())
            
            # Check if the assistant wants to use tools
            if assistant_message.tool_calls:
                print('Using tools to complete your request...')
                
                # Make the actual tool calls to our server
                tool_results = []
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    if function_name == "create_product":
                        print('\nReady to create product with the following information:')
                        for key, value in function_args.items():
                            print(f'- {key}: {value}')
                        print('\nCreating product...')
                    elif function_name == "list_products":
                        print('\nListing all products...')
                    
                    print(f'Calling tool: {function_name}')
                    result = await call_product_tool(function_name, function_args)
                    
                    # Format the result for OpenAI
                    tool_result = {
                        'tool_call_id': tool_call.id,
                        'role': 'tool',
                        'name': function_name,
                        'content': result.get('content', [{}])[0].get('text', str(result))
                    }
                    tool_results.append(tool_result)
                    messages.append(tool_result)
                
                # Display the tool results
                for result in tool_results:
                    try:
                        if result['name'] == 'create_product':
                            product_data = json.loads(result['content'])
                            print('\n===== Product Created Successfully =====')
                            print(f'ID: {product_data["id"]}')
                            print(f'Title: {product_data["title"]}')
                            print(f'Short Description: {product_data["short_description"]}')
                            print(f'Long Description: {product_data["long_description"]}')
                            print('\nTicket Details:')
                            print(f'  ID: {product_data["ticket"]["id"]}')
                            print(f'  Price: ${product_data["ticket"]["price"]}')
                            print(f'  Type: {product_data["ticket"]["ticket_type"]["title"]} (ID: {product_data["ticket"]["ticket_type"]["id"]})')
                            print(f'  Category: {product_data["ticket"]["ticket_category"]["title"]} (ID: {product_data["ticket"]["ticket_category"]["id"]})')
                            print('======================================')
                        elif result['name'] == 'list_products':
                            data = json.loads(result['content'])
                            products = data.get('products', [])
                            print('\n===== Products List =====')
                            if not products:
                                print('No products found.')
                            else:
                                print(f'Found {len(products)} product(s):')
                                for idx, product in enumerate(products, 1):
                                    print(f'\n--- Product {idx} ---')
                                    print(f'ID: {product["id"]}')
                                    print(f'Title: {product["title"]}')
                                    print(f'Short Description: {product["short_description"]}')
                                    # Print only shorter details to avoid overwhelming output
                                    print(f'Ticket Type: {product["ticket"]["ticket_type"]["title"]}')
                                    print(f'Ticket Category: {product["ticket"]["ticket_category"]["title"]}')
                                    print(f'Price: ${product["ticket"]["price"]}')
                            print('========================')
                    except (json.JSONDecodeError, KeyError) as e:
                        print('\nTool response:', result['content'])
                        print(f'Error parsing response: {e}')
            else:
                # Just display the assistant's response
                print('\nAssistant:', assistant_message.content)
            
        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main()) 