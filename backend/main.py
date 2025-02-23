# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import redis
import json
import uuid
from typing import Dict, List, Optional
import httpx
import asyncio
from dataclasses import dataclass
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Data model for active sessions
@dataclass
class SessionInfo:
    channels: List[str]
    session_type: str
    connected_sockets: List[WebSocket] = None

    def __post_init__(self):
        if self.connected_sockets is None:
            self.connected_sockets = []

class WebSocketManager:
    def __init__(self):
        self.active_sessions: Dict[str, SessionInfo] = {}
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.redis_subscriber = self.redis_client.pubsub()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    def get_allowed_channels(self, session_id: str, session_type: str) -> List[str]:
        if session_type == 'Human/AI':
            return [
                f"Jack:Jane:{session_id}",
                f"Jane:Jack:{session_id}",
                f"Scene:Jack:{session_id}",
                f"Scene:Jane:{session_id}",
                f"Human:Jack:{session_id}",
                f"Jack:Human:{session_id}",
                f"Agent:Runtime:{session_id}",
                f"Runtime:Agent:{session_id}",
            ]
        return [
            f"Human:Jack:{session_id}",
            f"Jack:Human:{session_id}",
            f"Agent:Runtime:{session_id}",
            f"Runtime:Agent:{session_id}",
        ]

    async def create_session(self, websocket: WebSocket, session_type: str) -> str:
        session_id = str(uuid.uuid4())
        channels = self.get_allowed_channels(session_id, session_type)
        
        # Create session info
        self.active_sessions[session_id] = SessionInfo(
            channels=channels,
            session_type=session_type,
            connected_sockets=[websocket]
        )

        # Subscribe to Redis channels
        for channel in channels:
            self.redis_subscriber.subscribe(channel)

        print(f"New session created: {session_id}, Type: {session_type}")
        return session_id

    async def join_session(self, websocket: WebSocket, session_id: str) -> bool:
        if session_id not in self.active_sessions:
            return False
        
        self.active_sessions[session_id].connected_sockets.append(websocket)
        return True

    async def broadcast_to_session(self, session_id: str, message: dict):
        if session_id in self.active_sessions:
            dead_sockets = []
            for socket in self.active_sessions[session_id].connected_sockets:
                try:
                    await socket.send_json(message)
                except WebSocketDisconnect:
                    dead_sockets.append(socket)
            
            for dead_socket in dead_sockets:
                self.active_sessions[session_id].connected_sockets.remove(dead_socket)

    async def handle_redis_messages(self):
        """Background task to handle Redis messages"""
        while True:
            message = self.redis_subscriber.get_message(ignore_subscribe_messages=True)
            if message and message['type'] == 'message':
                channel = message['channel'].decode('utf-8')
                data = message['data'].decode('utf-8')
                
                # Find which session this message belongs to
                for session_id, session_info in self.active_sessions.items():
                    if channel in session_info.channels:
                        await self.broadcast_to_session(
                            session_id,
                            {"channel": channel, "message": data}
                        )
            
            await asyncio.sleep(0.1)

web_app = FastAPI()

# Configure CORS
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize WebSocket manager
ws_manager = WebSocketManager()

# Background task to handle Redis messages
@web_app.on_event("startup")
async def startup_event():
    asyncio.create_task(ws_manager.handle_redis_messages())

@web_app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down, cleaning up resources...")

    # Unsubscribe all Redis channels for all active sessions
    for session_id, session_info in list(ws_manager.active_sessions.items()):
        for channel in session_info.channels:
            ws_manager.redis_subscriber.unsubscribe(channel)
    
    # Close the Redis pubsub and client connections
    ws_manager.redis_subscriber.close()
    ws_manager.redis_client.close()

@web_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            command = data.get("command")
            
            if command == "create_session":
                session_id = await ws_manager.create_session(
                    websocket,
                    data.get("session_type")
                )
                await websocket.send_json({"session_id": session_id})

            elif command == "join_session":
                success = await ws_manager.join_session(
                    websocket,
                    data.get("session_id")
                )
                await websocket.send_json({"success": success})

            elif command == "chat_message":
                session_id = data.get("session_id")
                message = data.get("message")
                
                agent_action = {
                    "data": {
                        "agent_name": "user",
                        "action_type": "speak",
                        "argument": message,
                        "path": "",
                        "data_type": "agent_action"
                    }
                }
                ws_manager.redis_client.publish(
                    f"Human:Jack:{session_id}",
                    json.dumps(agent_action)
                )

            elif command == "save_file":
                session_id = data.get("session_id")
                path = data.get("path")
                content = data.get("content")
                
                save_message = {
                    "data": {
                        "agent_name": "user",
                        "action_type": "write",
                        "argument": content,
                        "path": path,
                        "data_type": "agent_action"
                    }
                }
                ws_manager.redis_client.publish(
                    f"Agent:Runtime:{session_id}",
                    json.dumps(save_message)
                )

            elif command == "terminal_command":
                print("Received terminal command:", data)
                session_id = data.get("session_id")
                cmd = data.get("input_command")
                
                message_envelope = {
                    "data": {
                        "agent_name": "user",
                        "action_type": "run",
                        "argument": cmd,
                        "path": "",
                        "data_type": "agent_action"
                    }
                }
                ws_manager.redis_client.publish(
                    f"Agent:Runtime:{session_id}",
                    json.dumps(message_envelope)
                )

            elif command == "init_agent_conversation":
                session_id = data.get("session_id")
                init_params = {
                    "redis_url": "redis://localhost:6379/0",
                    "extra_modules": [
                        "interview_case.interview_agent",
                        "interview_case.nodes.initial_message_node",
                        "interview_case.nodes.chat_print_node"
                    ],
                    "nodes": [
                        {
                            "node_name": "Jack",
                            "node_class": "llm_agent",
                            "node_args": {
                                "query_interval": 5,
                                "output_channel": f"Jack:Jane:{session_id}",
                                "input_text_channels": [f"Jane:Jack:{session_id}"],
                                "input_env_channels": [f"Scene:Jack:{session_id}", f"Runtime:Agent:{session_id}"],
                                "input_tick_channel": f"tick/secs/{session_id}",
                                "goal": "Your goal is to effectively test Jane's technical ability and finally decide if she has passed the interview. Make sure to also evaluate her communication skills, problem-solving approach, and enthusiasm.",
                                "model_name": "gpt-4o",
                                "agent_name": "Jack"
                            }
                        },
                        {
                            "node_name": "Jane",
                            "node_class": "llm_agent",
                            "node_args": {
                                "query_interval": 7,
                                "output_channel": f"Jane:Jack:{session_id}",
                                "input_text_channels": [f"Jack:Jane:{session_id}"],
                                "input_env_channels": [f"Scene:Jane:{session_id}", f"Runtime:Agent:{session_id}"],
                                "input_tick_channel": f"tick/secs/{session_id}",
                                "goal": "Your goal is to perform well in the interview by demonstrating your technical skills, clear communication, and enthusiasm for the position. Stay calm, ask clarifying questions when needed, and confidently explain your thought process.",
                                "model_name": "gpt-4o",
                                "agent_name": "Jane"
                            }
                        },
                        {
                            "node_name": "tick",
                            "node_class": "tick"
                        },
                        {
                            "node_name": "JaneScene",
                            "node_class": "initial_message",
                            "node_args": {
                                "input_tick_channel": f"tick/secs/{session_id}",
                                "output_channels": [f"Scene:Jane:{session_id}"],
                                "env_scenario": """You are Jane, a college senior at Stanford University interviewing for a Software Engineering Intern position at a Fintech company. 
                You are currently sitting in an office with your interviewer, Jack.
                It's natural to feel a bit nervous, but remind yourself that you have prepared well. 
                You are very good at PyTorch but do not know anything about JAX. Please ask questions and use the resources the interviewer provides.
                You MUST look into the mean and square documentation before implementing the function by using browse.
                You should also ask clarifying questions about the array shapes to the interviewer.
                Keep your conversations short and to the point and NEVER repeat yourself.
                You need to code using the JAX library. The initial question has some URLs to documentation that you can use to check the syntax.
                If you have a question about reshape syntax use: https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.reshape.html
                If you have a question about mean syntax: https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.mean.html
                If you have a question about concatenate: https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.concatenate.html
                If you have a question about square check: https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.square.html
                Run your code to verify the working."""
                            }
                        },
                        {
                            "node_name": "JackScene",
                            "node_class": "initial_message",
                            "node_args": {
                                "input_tick_channel": f"tick/secs/{session_id}",
                                "output_channels": [f"Scene:Jack:{session_id}"],
                                "env_scenario": """You are Jack, a Principal Software Engineer at a Fintech company with over 10 years of experience in the field. 
                You graduated from Stanford with a degree in Computer Science and have been with the Fintech company for the past 5 years.
                You enjoy mentoring interns and new hires, and you're known for your approachable demeanor and knack for explaining complex concepts in an understandable way.
                Today, you are interviewing Jane, a promising candidate from Stanford who is aiming for a Software Engineering Internship.
                TRY using none action to allow the interviewer to do her work UNLESS you need to provide feedback or do any action.
                If the interviewer takes no action for 2 turns, nudge them and see if they need help.
                Keep your conversations short and to the point and NEVER repeat yourself."""
                            }
                        },
                        {
                            "node_name": "chat_print",
                            "node_class": "chat_print",
                            "node_args": {
                                "print_channel_types": {
                                    f"Jane:Jack:{session_id}": "agent_action",
                                    f"Jack:Jane:{session_id}": "agent_action",
                                    f"Agent:Runtime:{session_id}": "agent_action"
                                },
                                "env_agents": ["Jack", "Jane"]
                            }
                        },
                        {
                            "node_name": "record",
                            "node_class": "record",
                            "node_args": {
                                "jsonl_file_path": "../logs/interview_openhands.jsonl",
                                "record_channel_types": {
                                    f"Jane:Jack:{session_id}": "agent_action",
                                    f"Jack:Jane:{session_id}": "agent_action",
                                    f"Agent:Runtime:{session_id}": "agent_action",
                                    f"Runtime:Agent:{session_id}": "text",
                                    f"Scene:Jane:{session_id}": "text",
                                    f"Scene:Jack:{session_id}": "text"
                                }
                            }
                        }
                    ]
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:9000/init-agents",
                        json=init_params
                    )
                    result = response.json()
                    await websocket.send_json({
                        "success": result.get("status") == "success"
                    })

            elif command == "init_process":
                session_id = data.get("session_id")
                init_params = {
                    "node_name": "openhands_node",
                    "input_channels": [f"Agent:Runtime:{session_id}"],
                    "output_channels": [f"Runtime:Agent:{session_id}"],
                    "modal_session_id": session_id
                }
                
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.post(
                            "http://localhost:5000/initialize",
                            json=init_params,
                            timeout=300.0
                        )
                        result = response.json()
                        await websocket.send_json({
                            "success": result.get("status") == "initialized",
                            "session_id": session_id
                        })
                    except httpx.HTTPError as e:
                        print(f"Error: {e}")
                        await websocket.send_json({
                            "success": False,
                            "error": str(e)
                        })
                        continue

            elif command == "kill_session":
                session_id = data.get("session_id")
                if session_id in ws_manager.active_sessions:
                    # Unsubscribe from Redis channels
                    for channel in ws_manager.active_sessions[session_id].channels:
                        ws_manager.redis_subscriber.unsubscribe(channel)
                    
                    # Notify all connected clients
                    await ws_manager.broadcast_to_session(
                        session_id,
                        {"type": "session_terminated"}
                    )
                    
                    # Remove session
                    del ws_manager.active_sessions[session_id]
                    await websocket.send_json({"success": True})

    except WebSocketDisconnect:
        print("Client disconnected")
        # Clean up any sessions where this was the last connected client
        for session_id, session_info in list(ws_manager.active_sessions.items()):
            session_info.connected_sockets = [
                sock for sock in session_info.connected_sockets 
                if sock != websocket
            ]
            if not session_info.connected_sockets:
                del ws_manager.active_sessions[session_id]

def start_server(port: int):
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    start_server(port)