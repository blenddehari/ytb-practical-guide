import asyncio
import httpx
import json

# The server URL from the servers.yaml
SERVER_URL = "http://localhost:8001/sse"
API_KEY = "secret-key3"

async def test_connection():
    # Test the server with direct HTTP requests
    async with httpx.AsyncClient() as client:
        # Test the initialize request
        print(f"Testing initialize request to {SERVER_URL}")
        response = await client.post(
            SERVER_URL,
            json={"type": "initialize", "id": "test-id"},
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        print(f"Initialize response: {response.status_code}")
        print(response.json())
        
        # Test the list_tools request
        print("\nTesting list_tools request")
        response = await client.post(
            SERVER_URL,
            json={"type": "list_tools", "id": "test-id2"},
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        print(f"List tools response: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(test_connection()) 