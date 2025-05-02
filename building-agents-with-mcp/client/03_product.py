import asyncio
import os
import json

from dotenv import load_dotenv
from openai import OpenAI
from utils.client_manager import ClientManager

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

model = os.getenv('MODEL', 'gpt-4o')


async def main():
	client_manager = ClientManager()
	client_manager.load_servers('servers.yaml')

	await client_manager.connect_to_server()

	# Display available tools
	print('\n=== Product Creation Assistant ===')
	print('This assistant will help you create products using the following tools:')
	for tool in client_manager.tools:
		if tool['function']['name'] == 'create_product':
			print(f'- {tool["function"]["name"]}: {tool["function"]["description"]}')
			print('  Required information:')
			for param, details in tool['function']['parameters']['properties'].items():
				required = '(required)' if param in tool['function']['parameters'].get('required', []) else '(optional)'
				print(f'    - {param}: {details["description"]} {required}')

	# Initial user query
	print('\nYou can start by describing the product you want to create.')
	print('Example: "Create a concert ticket for the Summer Festival"')
	query = input('\nWhat would you like to do? ')
	
	# Start conversation
	messages = [{'role': 'user', 'content': query}]
	
	# Continue conversation until user is done
	while True:
		try:
			print('\nSending request to OpenAI...')
			response = client.chat.completions.create(
				model=model,
				messages=messages,
				tools=client_manager.tools,
				tool_choice='auto',
				temperature=0.0,
			)
			
			# Get the assistant's message
			assistant_message = response.choices[0].message
			messages.append(assistant_message.model_dump())
			
			# Check if the assistant wants to use tools
			if assistant_message.tool_calls:
				print('\nAssistant is gathering required information...')
				
				# Print what information is being used
				for tool_call in assistant_message.tool_calls:
					function_args = json.loads(tool_call.function.arguments)
					print('\nReady to create product with the following information:')
					for key, value in function_args.items():
						print(f'- {key}: {value}')
				
				print('\nCreating product...')
				results = await client_manager.process_tool_call(assistant_message.tool_calls)
				
				# Add tool response to messages
				for result in results:
					messages.append({
						'role': 'tool',
						'tool_call_id': result['tool_call_id'],
						'name': result['name'],
						'content': result['content']
					})
					
					# Pretty print the tool response
					try:
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
					except json.JSONDecodeError:
						print('\nTool response:', result['content'])
			else:
				# Just display the assistant's response
				print('\nAssistant:', assistant_message.content)
			
			# Ask if user wants to continue
			should_continue = input('\nDo you want to continue? (y/n): ').lower()
			if should_continue != 'y':
				break
				
			# Get next user query
			query = input('\nEnter your next query: ')
			messages.append({'role': 'user', 'content': query})
			
		except Exception as e:
			print(f'Error: {e}')
			import traceback
			traceback.print_exc()
			break

	await client_manager.cleanup()


if __name__ == '__main__':
	asyncio.run(main()) 