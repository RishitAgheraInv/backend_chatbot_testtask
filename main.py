from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import json
import asyncio
from typing import List

from database import get_db, engine
from models import Base, User, Conversation, Message
from schemas import (
    UserCreate, UserResponse, ConversationCreate, ConversationResponse,
    MessageResponse, ChatRequest, ChatResponse
)
from crud import UserCRUD, ConversationCRUD, MessageCRUD
from chatbot import StreamingChatbot
from websocket_manager import manager

# Create tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up the chatbot application...")
    yield
    # Shutdown
    print("Shutting down the chatbot application...")


app = FastAPI(
    title="Streaming Chatbot API",
    description="A streaming chatbot API with user-specific conversations",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for React integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chatbot
chatbot = StreamingChatbot()


@app.get("/")
async def root():
    return {"message": "Streaming Chatbot API is running!"}


@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    existing_user = UserCRUD.get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email already registered"
        )

    return UserCRUD.create_user(db, user)


@app.get("/users/{username}", response_model=UserResponse)
async def get_user(username: str, db: Session = Depends(get_db)):
    """Get user by username"""
    user = UserCRUD.get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@app.post("/users/{user_id}/conversations/", response_model=ConversationResponse)
async def create_conversation(
        user_id: int,
        conversation: ConversationCreate,
        db: Session = Depends(get_db)
):
    """Create a new conversation for a user"""
    user = UserCRUD.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return ConversationCRUD.create_conversation(db, user_id, conversation.title)


@app.get("/users/{user_id}/conversations/", response_model=List[ConversationResponse])
async def get_user_conversations(user_id: int, db: Session = Depends(get_db)):
    """Get all conversations for a user"""
    user = UserCRUD.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return ConversationCRUD.get_user_conversations(db, user_id)


@app.get("/conversations/{conversation_id}/messages/", response_model=List[MessageResponse])
async def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db)):
    """Get all messages in a conversation"""
    conversation = ConversationCRUD.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    return MessageCRUD.get_conversation_messages(db, conversation_id)


@app.post("/chat/stream/{user_id}")
async def stream_chat(
        user_id: int,
        chat_request: ChatRequest,
        db: Session = Depends(get_db)
):
    """Stream chat response word by word"""

    # Verify user exists
    user = UserCRUD.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get or create conversation
    if chat_request.conversation_id:
        conversation = ConversationCRUD.get_conversation(db, chat_request.conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        # Create new conversation
        conversation = ConversationCRUD.create_conversation(db, user_id, "New Chat")

    # Save user message
    user_message = MessageCRUD.create_message(
        db, conversation.id, "user", chat_request.message
    )

    # Get conversation history
    messages = MessageCRUD.get_messages_as_dict(db, conversation.id)

    async def generate_response():
        full_response = ""

        # Send conversation ID first
        yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': conversation.id})}\n\n"

        try:
            async for chunk_data in chatbot.stream_response(messages):
                chunk = chunk_data["chunk"]
                full_response = chunk_data["full_response"]

                # Send chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

                # Add small delay to simulate realistic streaming
                await asyncio.sleep(0.01)

            # Save assistant response
            MessageCRUD.create_message(
                db, conversation.id, "assistant", full_response
            )

            # Send completion signal
            yield f"data: {json.dumps({'type': 'complete', 'full_response': full_response})}\n\n"

        except Exception as e:
            # Send error
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        # Send end signal
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )


@app.post("/chat/{user_id}", response_model=ChatResponse)
async def chat(
        user_id: int,
        chat_request: ChatRequest,
        db: Session = Depends(get_db)
):
    """Regular chat endpoint (non-streaming)"""

    # Verify user exists
    user = UserCRUD.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get or create conversation
    if chat_request.conversation_id:
        conversation = ConversationCRUD.get_conversation(db, chat_request.conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        # Create new conversation
        conversation = ConversationCRUD.create_conversation(db, user_id, "New Chat")

    # Save user message
    user_message = MessageCRUD.create_message(
        db, conversation.id, "user", chat_request.message
    )

    # Get conversation history
    messages = MessageCRUD.get_messages_as_dict(db, conversation.id)

    # Generate response
    response = chatbot.get_response(messages)

    # Save assistant response
    MessageCRUD.create_message(
        db, conversation.id, "assistant", response
    )

    return ChatResponse(
        conversation_id=conversation.id,
        message=response
    )


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time chat"""

    # Get database session
    db = next(get_db())

    try:
        # Verify user exists
        user = UserCRUD.get_user_by_id(db, user_id)
        if not user:
            await websocket.close(code=4004, reason="User not found")
            return

        # Connect to WebSocket
        await manager.connect(websocket, user_id)

        # Send welcome message
        await manager.send_message({
            "type": "connection",
            "message": f"Connected to chat server",
            "user_id": user_id
        }, websocket)

        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Validate message format
            if "message" not in message_data:
                await manager.send_message({
                    "type": "error",
                    "message": "Invalid message format. Expected: {\"message\": \"text\", \"conversation_id\": optional}"
                }, websocket)
                continue

            user_message = message_data["message"]
            conversation_id = message_data.get("conversation_id")
            # print("Conversation_id:",conversation_id)
            # Get or create conversation
            if conversation_id:
                conversation = ConversationCRUD.get_conversation(db, conversation_id)
                if not conversation or conversation.user_id != user_id:
                    await manager.send_message({
                        "type": "error",
                        "message": "Conversation not found or access denied"
                    }, websocket)
                    continue
            else:
                # Create new conversation
                conversation = ConversationCRUD.create_conversation(db, user_id, user_message[:15])
                await manager.send_message({
                    "type": "conversation_created",
                    "conversation_id": conversation.id
                }, websocket)

            # Save user message
            MessageCRUD.create_message(db, conversation.id, "user", user_message)

            # Send user message confirmation
            await manager.send_message({
                "type": "user_message",
                "conversation_id": conversation.id,
                "message": user_message
            }, websocket)

            # Get conversation history
            messages = MessageCRUD.get_messages_as_dict(db, conversation.id)

            # Send typing indicator
            await manager.send_message({
                "type": "typing",
                "conversation_id": conversation.id
            }, websocket)

            # Generate and stream response
            full_response = ""
            try:
                async for chunk_data in chatbot.stream_response(messages):
                    chunk = chunk_data["chunk"]
                    full_response = chunk_data["full_response"]

                    # Send chunk to client
                    await manager.send_message({
                        "type": "chunk",
                        "conversation_id": conversation.id,
                        "content": chunk,
                        "full_response": full_response
                    }, websocket)

                    # Small delay for realistic streaming
                    await asyncio.sleep(0.01)

                # Save assistant response
                MessageCRUD.create_message(db, conversation.id, "assistant", full_response)

                # Send completion message
                await manager.send_message({
                    "type": "message_complete",
                    "conversation_id": conversation.id,
                    "full_response": full_response
                }, websocket)

            except Exception as e:
                await manager.send_message({
                    "type": "error",
                    "message": f"Error generating response: {str(e)}"
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.send_message({
            "type": "error",
            "message": f"Server error: {str(e)}"
        }, websocket)
    finally:
        db.close()


@app.get("/ws/users/{user_id}/status")
async def get_websocket_status(user_id: int):
    """Get WebSocket connection status for a user"""
    print("Hello")
    connections = len(manager.active_connections.get(user_id, []))
    return {
        "user_id": user_id,
        "active_connections": connections,
        "is_online": connections > 0
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )