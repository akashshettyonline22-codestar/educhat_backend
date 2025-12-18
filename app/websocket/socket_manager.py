from socketio import AsyncServer
from fastapi import FastAPI
import logging
from app.routers.qa_router import ask_question_chatbot
from app.middleware.auth_middleware import decode_token_simple
from datetime import datetime




logger = logging.getLogger(__name__)

# Create Socket.IO server
sio = AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # In production, use specific origins
    logger=True,
    engineio_logger=True
)

# Store active connections
active_connections = {}

@sio.event
async def connect(sid, environ, auth):
    """Handle new socket connections with JWT authentication"""
    print(f"\n🔌 New connection attempt: {sid}")
    print(f"Auth data: {auth}")
    
    try:
        # Extract token from auth data
        token = auth.get('token') if auth else None
        
        if not token:
            print(f"❌ No token provided")
            await sio.disconnect(sid)
            return False
        
        # ✅ Use the new decoder function
        user_email = decode_token_simple(token)
        
        if not user_email:
            print(f"❌ Invalid token")
            await sio.disconnect(sid)
            return False
        
        print(f"✅ Token verified for user: {user_email}")
        
        # Store connection with user info
        active_connections[sid] = {
            'user_email': user_email,
            'connected_at': str(datetime.now())
        }
        
        print(f"✅ Socket connected: {sid} (User: {user_email})")
        print(f"📊 Active connections: {len(active_connections)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        import traceback
        traceback.print_exc()
        await sio.disconnect(sid)
        return False

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    logger.info(f"❌ Client disconnected: {sid}")
    if sid in active_connections:
        del active_connections[sid]
    print(f"Active connections: {len(active_connections)}")

@sio.event
async def chat_message(sid, data):
    """Handle incoming chat messages"""
    print(f"📥 📥 📥 RECEIVED MESSAGE from {sid}")
    print(f"Data: {data}")
    
    bot_id = data.get('bot_id')
    message = data.get('message')
    conversation_id = data.get('conversation_id')
    
    print(f"Bot ID: {bot_id}, Message: {message}")
    
    try:
        # Send typing indicator
        await sio.emit('bot_typing', {'typing': True}, room=sid)
        
        # Get user email from authenticated connection
        user_info = active_connections.get(sid)
       
        if not user_info:
            print(f"❌ No user info for {sid}")
            raise Exception("User not authenticated")
        
        user_email = user_info.get('user_email')
        print(f"👤 Authenticated user: {user_email}")
        
        # Create mock request with real user email
        class MockState:
            def __init__(self, email):
                self.current_user_email = email
        
        class MockRequest:
            def __init__(self, email):
                self.state = MockState(email)
        
        # Call chatbot function
        print(f"🤖 Calling ask_question_chatbot for {user_email}...")
        response = await ask_question_chatbot(
            request=MockRequest(user_email),
            textbook_id=bot_id,
            question=message,
            # session_id=conversation_id,
            token="dummy_token"  # We'll fix auth later
        )
        print(response)
        print(f"✅ Got response object: {type(response)}")
        
        # Extract answer
        bot_response = response.answer if hasattr(response, 'answer') else str(response)
        print(f"✅ Bot response: {bot_response[:100]}...")
        educational_image = response.educational_image if hasattr(response, 'educational_image') else None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        bot_response = f"Sorry, error: {str(e)}"
    
    # Send response
    await sio.emit('bot_response', {
        'message': bot_response,
        'bot_id': bot_id,
        'conversation_id': conversation_id,
        'educational_image': educational_image,
    }, room=sid)
    
    print(f"📤 Sent response")

def get_socket_app(app: FastAPI):
    """Integrate Socket.IO with FastAPI"""
    import socketio
    return socketio.ASGIApp(
        socketio_server=sio,
        other_asgi_app=app,
        socketio_path='socket.io'
    )
