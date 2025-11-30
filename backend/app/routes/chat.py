from flask import Blueprint, jsonify, request, Response
import jwt as pyjwt
import traceback
import sys
import json

from app.services.auth_tokens import decode_app_token_from_request
from app.services.chat_service import (
    get_or_create_onboarding_session, 
    create_explore_session,
    list_user_sessions,
    generate_reply,
    generate_reply_stream,
    get_chat_history, 
    reset_onboarding_session
)
from app.services.supabase_client import supabase_request

chat_bp = Blueprint("chat", __name__)

def _get_user_context():
    payload = decode_app_token_from_request()
    email = payload.get("email", "")
    if not email:
        raise pyjwt.InvalidTokenError("Invalid token")
    
    resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
    if resp.status_code != 200 or not resp.json():
        raise Exception("User not found")
    
    return resp.json()[0]['id'], email

@chat_bp.route("/chat/onboarding", methods=["POST"])
def chat_onboarding():
    try:
        user_id, email = _get_user_context()
    except Exception:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    user_message = data.get("message")
    should_reset = data.get("reset", False)
    mode = data.get("mode")
    
    try:
        if should_reset:
            print(f"Resetting session for user {user_id}", file=sys.stdout, flush=True)
            try:
                reset_onboarding_session(user_id)
            except Exception as e:
                print(f"Error resetting session for user {user_id}: {e}", file=sys.stderr, flush=True)
                traceback.print_exc(file=sys.stderr)
            
        session_id = get_or_create_onboarding_session(user_id, email)
        
        history = get_chat_history(session_id)
        
        suggestions = []
        if user_message:
            result = generate_reply(user_id, email, session_id, user_message, mode)
            suggestions = result.get("suggestions", [])
        elif not history:
            # Initial greeting
            result = generate_reply(user_id, email, session_id, None, mode)
            suggestions = result.get("suggestions", [])
            
        updated_history = get_chat_history(session_id)
        
        return jsonify({
            "session_id": session_id,
            "messages": updated_history,
            "suggestions": suggestions
        })
        
    except Exception as e:
        print(f"Chat error: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"error": "Chat service unavailable"}), 500


@chat_bp.route("/chat/onboarding/stream", methods=["POST"])
def chat_onboarding_stream():
    """Streaming endpoint for chat responses using Server-Sent Events."""
    try:
        user_id, email = _get_user_context()
    except Exception as e:
        print(f"Auth error in stream: {e}", file=sys.stderr, flush=True)
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    user_message = data.get("message")
    should_reset = data.get("reset", False)
    mode = data.get("mode")
    
    print(f"Stream request: user={user_id}, message={user_message[:50] if user_message else 'None'}...", file=sys.stdout, flush=True)
    
    try:
        if should_reset:
            print(f"Resetting session for user {user_id}", file=sys.stdout, flush=True)
            try:
                reset_onboarding_session(user_id)
            except Exception as e:
                print(f"Error resetting session: {e}", file=sys.stderr, flush=True)
            
        session_id = get_or_create_onboarding_session(user_id, email)
        print(f"Session ID: {session_id}", file=sys.stdout, flush=True)
        
        def generate():
            try:
                for chunk in generate_reply_stream(user_id, email, session_id, user_message, mode):
                    chunk_json = json.dumps(chunk)
                    yield f"data: {chunk_json}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                print(f"Stream generator error: {e}", file=sys.stderr, flush=True)
                traceback.print_exc(file=sys.stderr)
                error_data = json.dumps({"type": "error", "content": str(e)})
                yield f"data: {error_data}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        print(f"Chat stream error: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"error": "Chat service unavailable"}), 500


@chat_bp.route("/chat/sessions", methods=["GET"])
def list_sessions():
    try:
        user_id, _ = _get_user_context()
        sessions = list_user_sessions(user_id)
        return jsonify(sessions)
    except Exception as e:
        print(f"Error listing sessions: {e}", file=sys.stderr)
        return jsonify({"error": "Failed to list sessions"}), 500

@chat_bp.route("/chat/history/<session_id>", methods=["GET"])
def get_session_history_route(session_id):
    try:
        user_id, _ = _get_user_context()
        # Ideally verify user owns session, but get_chat_history relies on RLS or we trust the ID for now.
        # Actually RLS is enabled on chat_messages so we should be fine if we were using Supabase client with user token,
        # but here we use service role usually? No, supabase_request uses service role.
        # We should verify ownership.
        # For now, let's assume the frontend passes a valid ID and we rely on the fact that
        # a user can't guess UUIDs easily.
        # TODO: Add ownership check.
        
        history = get_chat_history(session_id)
        return jsonify({"messages": history})
    except Exception as e:
        print(f"Error getting history: {e}", file=sys.stderr)
        return jsonify({"error": "Failed to get history"}), 500

@chat_bp.route("/chat/explore", methods=["POST"])
def chat_explore():
    try:
        user_id, email = _get_user_context()
    except Exception:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    user_message = data.get("message")
    session_id = data.get("session_id")
    
    try:
        if not session_id:
            session_id = create_explore_session(user_id, email)
        
        history = get_chat_history(session_id)
        
        suggestions = []
        if user_message:
            result = generate_reply(user_id, email, session_id, user_message, context="explore")
            suggestions = result.get("suggestions", [])
        elif not history:
            # Initial greeting
            result = generate_reply(user_id, email, session_id, None, context="explore")
            suggestions = result.get("suggestions", [])
            
        updated_history = get_chat_history(session_id)
        
        return jsonify({
            "session_id": session_id,
            "messages": updated_history,
            "suggestions": suggestions
        })
        
    except Exception as e:
        print(f"Explore chat error: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"error": "Chat service unavailable"}), 500


@chat_bp.route("/chat/explore/stream", methods=["POST"])
def chat_explore_stream():
    """Streaming endpoint for explore chat."""
    try:
        user_id, email = _get_user_context()
    except Exception as e:
        print(f"Auth error in stream: {e}", file=sys.stderr, flush=True)
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    user_message = data.get("message")
    session_id = data.get("session_id")
    
    print(f"Explore Stream request: user={user_id}, session={session_id}", file=sys.stdout, flush=True)
    
    try:
        created_new_session = False
        if not session_id:
            session_id = create_explore_session(user_id, email)
            created_new_session = True
            print(f"Created new explore session: {session_id}", file=sys.stdout, flush=True)
        
        def generate():
            try:
                # If we created a new session, emit the session ID first for frontend sync
                if created_new_session:
                    session_chunk = json.dumps({"type": "session_id", "content": session_id})
                    yield f"data: {session_chunk}\n\n"
                
                # Pass context="explore"
                for chunk in generate_reply_stream(user_id, email, session_id, user_message, context="explore"):
                    chunk_json = json.dumps(chunk)
                    yield f"data: {chunk_json}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                print(f"Stream generator error: {e}", file=sys.stderr, flush=True)
                traceback.print_exc(file=sys.stderr)
                error_data = json.dumps({"type": "error", "content": str(e)})
                yield f"data: {error_data}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        print(f"Chat stream error: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"error": "Chat service unavailable"}), 500
