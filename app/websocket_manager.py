from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio


class ConnectionManager:
    def __init__(self):
        # Store active connections: {user_id: [websocket_connections]}
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept websocket connection and add to user's connections"""
        print("websocket connect")
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)
        print(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove websocket connection"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)

            # Remove user entry if no connections left
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        print(f"User {user_id} disconnected")

    async def send_message(self, message: dict, websocket: WebSocket):
        """Send message to specific websocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"Error sending message: {e}")

    async def send_to_user(self, message: dict, user_id: int):
        """Send message to all connections of a user"""
        if user_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(websocket)

            # Remove disconnected websockets
            for ws in disconnected:
                self.active_connections[user_id].remove(ws)

    async def broadcast_to_user(self, message: dict, user_id: int):
        """Broadcast message to all user's connections"""
        await self.send_to_user(message, user_id)


# Global connection manager instance
manager = ConnectionManager()