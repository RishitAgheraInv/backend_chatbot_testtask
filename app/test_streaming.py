import requests
import json
import asyncio
import aiohttp
import time

BASE_URL = "http://localhost:8000"


def test_create_user():
    """Test creating a user"""
    user_data = {
        "username": "testuser11",
        "email": "test11@example.com"
    }

    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    print(f"Create User Response: {response.status_code}")
    if response.status_code == 200:
        user = response.json()
        print(f"Created user: {user}")
        return user
    else:
        print(f"Error: {response.text}")
        return None


def test_regular_chat(user_id):
    """Test regular chat endpoint"""
    chat_data = {
        "message": "Hello! Can you tell me a joke?"
    }

    response = requests.post(f"{BASE_URL}/chat/{user_id}", json=chat_data)
    print(f"Regular Chat Response: {response.status_code}")
    if response.status_code == 200:
        chat_response = response.json()
        print(f"Chat Response: {chat_response}")
        return chat_response["conversation_id"]
    else:
        print(f"Error: {response.text}")
        return None


async def test_streaming_chat(user_id, conversation_id=None):
    """Test streaming chat endpoint"""
    chat_data = {
        "message": "Tell me a story about a robot learning to paint.",
        "conversation_id": conversation_id
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
                f"{BASE_URL}/chat/stream/{user_id}",
                json=chat_data,
                headers={"Accept": "text/event-stream"}
        ) as response:
            print(f"Streaming Chat Response: {response.status}")

            if response.status == 200:
                print("\n--- Streaming Response ---")
                full_response = ""

                async for line in response.content:
                    line = line.decode('utf-8').strip()

                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix

                        if data_str == "[DONE]":
                            print("\n--- Stream Complete ---")
                            break

                        try:
                            data = json.loads(data_str)

                            if data['type'] == 'conversation_id':
                                print(f"Conversation ID: {data['conversation_id']}")

                            elif data['type'] == 'chunk':
                                print(data['content'], end='', flush=True)
                                full_response += data['content']

                            elif data['type'] == 'complete':
                                print(f"\n\nFull Response: {data['full_response']}")

                            elif data['type'] == 'error':
                                print(f"\nError: {data['message']}")

                        except json.JSONDecodeError:
                            print(f"Could not parse: {data_str}")
            else:
                print(f"Error: {response.status}")


def test_get_conversations(user_id):
    """Test getting user conversations"""
    response = requests.get(f"{BASE_URL}/users/{user_id}/conversations/")
    print(f"Get Conversations Response: {response.status_code}")
    if response.status_code == 200:
        conversations = response.json()
        print(f"Conversations: {conversations}")
        return conversations
    else:
        print(f"Error: {response.text}")
        return None


async def main():
    """Run all tests"""
    print("=== Testing Chatbot API ===\n")

    # Test 1: Create user
    print("1. Creating user...")
    user = test_create_user()
    if not user:
        print("Failed to create user. Exiting.")
        return

    user_id = user["id"]
    print(f"User ID: {user_id}\n")

    # Test 2: Regular chat
    print("2. Testing regular chat...")
    conversation_id = test_regular_chat(user_id)
    print(f"Conversation ID: {conversation_id}\n")

    # Test 3: Streaming chat
    print("3. Testing streaming chat...")
    await test_streaming_chat(user_id, conversation_id)
    print("\n")

    # Test 4: Get conversations
    print("4. Getting user conversations...")
    conversations = test_get_conversations(user_id)
    print("\n")

    # Test 5: Another streaming chat in the same conversation
    print("5. Testing another streaming message in same conversation...")
    await test_streaming_chat(user_id, conversation_id)


if __name__ == "__main__":
    asyncio.run(main())