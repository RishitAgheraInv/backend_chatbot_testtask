import asyncio
import websockets
import json
import requests

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


def create_test_user():
    """Create a test user"""
    user_data = {
        "username": f"testuser_{asyncio.get_event_loop().time()}",
        "email": f"test{asyncio.get_event_loop().time()}@example.com"
    }

    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    if response.status_code == 200:
        user = response.json()
        print(f"Created user: {user['username']} (ID: {user['id']})")
        return user["id"]
    else:
        print(f"Error creating user: {response.text}")
        return None


async def test_websocket_chat(user_id):
    """Test WebSocket chat functionality"""

    uri = f"{WS_URL}/ws/{user_id}"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to WebSocket for user {user_id}")

            # Listen for welcome message
            welcome_message = await websocket.recv()
            welcome_data = json.loads(welcome_message)
            print(f"Server: {welcome_data}")

            # Test messages
            test_messages = [
                "Hello! Can you tell me a joke?",
                "That's funny! Tell me another one.",
                "What's the weather like on Mars?"
            ]

            conversation_id = None

            for i, message in enumerate(test_messages, 1):
                print(f"\n--- Test Message {i} ---")

                # Prepare message
                message_data = {"message": message}
                if conversation_id:
                    message_data["conversation_id"] = conversation_id

                # Send message
                await websocket.send(json.dumps(message_data))
                print(f"Sent: {message}")

                # Receive responses
                response_text = ""
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        data = json.loads(response)

                        if data["type"] == "conversation_created":
                            conversation_id = data["conversation_id"]
                            print(f"New conversation created: {conversation_id}")

                        elif data["type"] == "user_message":
                            print(f"User message confirmed: {data['message']}")

                        elif data["type"] == "typing":
                            print("Assistant is typing...")

                        elif data["type"] == "chunk":
                            print(data["content"], end="", flush=True)
                            response_text += data["content"]

                        elif data["type"] == "message_complete":
                            print(f"\n✓ Response complete")
                            break

                        elif data["type"] == "error":
                            print(f"Error: {data['message']}")
                            break

                    except asyncio.TimeoutError:
                        print("Timeout waiting for response")
                        break
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        break

                # Wait a bit before next message
                await asyncio.sleep(1)

            print("\n--- WebSocket Test Complete ---")

    except websockets.exceptions.ConnectionClosed:
        print("WebSocket connection closed")
    except Exception as e:
        print(f"WebSocket error: {e}")


async def test_multiple_connections(user_id):
    """Test multiple WebSocket connections for same user"""

    async def client_session(client_id):
        uri = f"{WS_URL}/ws/{user_id}"
        try:
            async with websockets.connect(uri) as websocket:
                print(f"Client {client_id} connected")

                # Send a message
                message_data = {"message": f"Hello from client {client_id}"}
                await websocket.send(json.dumps(message_data))

                # Receive responses
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        data = json.loads(response)

                        if data["type"] == "chunk":
                            print(f"Client {client_id}: {data['content']}", end="", flush=True)
                        elif data["type"] == "message_complete":
                            print(f"\nClient {client_id}: Complete")
                            break
                        elif data["type"] == "error":
                            print(f"Client {client_id} Error: {data['message']}")
                            break
                    except asyncio.TimeoutError:
                        break
        except Exception as e:
            print(f"Client {client_id} error: {e}")

    # Run multiple clients concurrently
    await asyncio.gather(
        client_session(1),
        client_session(2),
        # client_session(3)
    )


def check_websocket_status(user_id):
    """Check WebSocket connection status"""
    response = requests.get(f"{BASE_URL}/ws/users/{user_id}/status")
    if response.status_code == 200:
        status = response.json()
        print(f"WebSocket Status: {status}")
        return status
    else:
        print(f"Error checking status: {response.text}")
        return None


async def main():
    """Run WebSocket tests"""
    print("=== WebSocket Chat Test ===\n")

    # Create test user
    user_id = create_test_user()
    if not user_id:
        print("Failed to create user. Exiting.")
        return

    # Check initial status
    print("\n1. Checking initial WebSocket status...")
    check_websocket_status(user_id)

    # Test single connection
    print("\n2. Testing single WebSocket connection...")
    await test_websocket_chat(user_id)

    # Check status after disconnect
    print("\n3. Checking status after disconnect...")
    check_websocket_status(user_id)

    # Test multiple connections
    print("\n4. Testing multiple WebSocket connections...")
    await test_multiple_connections(user_id)


if __name__ == "__main__":
    asyncio.run(main())