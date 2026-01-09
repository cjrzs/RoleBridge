"""
WebSocket API - Real-time communication for Agent
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Optional
import json
import asyncio
from core.agent import TranslationAgent
from schemas.translate import TranslateRequest


router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """
        Accept and store WebSocket connection
        
        Args:
            websocket: WebSocket connection
            connection_id: Unique connection ID
        """
        await websocket.accept()
        self.active_connections[connection_id] = websocket
    
    def disconnect(self, connection_id: str):
        """
        Remove WebSocket connection
        
        Args:
            connection_id: Connection ID
        """
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
    
    async def send_message(self, connection_id: str, message: Dict):
        """
        Send message to specific connection
        
        Args:
            connection_id: Connection ID
            message: Message dictionary
        """
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error sending message to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def broadcast(self, message: Dict):
        """
        Broadcast message to all connections
        
        Args:
            message: Message dictionary
        """
        disconnected = []
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to {connection_id}: {e}")
                disconnected.append(connection_id)
        
        for connection_id in disconnected:
            self.disconnect(connection_id)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/translate")
async def websocket_translate(websocket: WebSocket):
    """
    WebSocket endpoint for translation with Agent
    
    Message format:
    - Client -> Server:
        {
            "type": "start_translation",
            "data": {
                "content": "...",
                "target_role": "...",
                "source_role": "..." (optional)
            }
        }
        {
            "type": "confirmation_response",
            "data": {
                "request_id": "...",
                "response": "..."
            }
        }
    
    - Server -> Client:
        {
            "type": "thinking",
            "data": {...}
        }
        {
            "type": "action",
            "data": {...}
        }
        {
            "type": "observation",
            "data": {...}
        }
        {
            "type": "decision",
            "data": {...}
        }
        {
            "type": "confirmation_request",
            "data": {...}
        }
        {
            "type": "translation_chunk",
            "data": "..."
        }
        {
            "type": "completed",
            "data": {...}
        }
        {
            "type": "error",
            "data": {"error": "..."}
        }
    """
    import uuid
    connection_id = str(uuid.uuid4())
    
    await manager.connect(websocket, connection_id)
    
    agent: Optional[TranslationAgent] = None
    confirmation_requests: Dict[str, asyncio.Event] = {}
    
    def websocket_send(message: Dict):
        """Callback for Agent to send messages via WebSocket"""
        asyncio.create_task(manager.send_message(connection_id, message))
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            message_data = data.get("data", {})
            
            if message_type == "start_translation":
                # Start translation task
                try:
                    content = message_data.get("content")
                    target_role = message_data.get("target_role")
                    source_role = message_data.get("source_role")
                    
                    if not content or not target_role:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"error": "Missing required fields: content, target_role"}
                        })
                        continue
                    
                    # Create Agent instance
                    agent = TranslationAgent(websocket_send=websocket_send)
                    
                    # Run Agent in background
                    async def run_agent():
                        try:
                            async for update in agent.run_stream(
                                content=content,
                                target_role=target_role,
                                source_role=source_role
                            ):
                                await websocket.send_json(update)
                        except Exception as e:
                            await websocket.send_json({
                                "type": "error",
                                "data": {"error": str(e)}
                            })
                    
                    asyncio.create_task(run_agent())
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"error": str(e)}
                    })
            
            elif message_type == "confirmation_response":
                # Handle confirmation response
                request_id = message_data.get("request_id")
                response = message_data.get("response")
                
                if request_id and agent:
                    # Set response in confirmation manager
                    agent.confirmation_manager.respond_to_request(request_id, response)
                    
                    # Signal waiting task
                    if request_id in confirmation_requests:
                        confirmation_requests[request_id].set()
                        del confirmation_requests[request_id]
            
            elif message_type == "ping":
                # Heartbeat
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": f"Unknown message type: {message_type}"}
                })
    
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(connection_id)
        try:
            await websocket.close()
        except:
            pass

