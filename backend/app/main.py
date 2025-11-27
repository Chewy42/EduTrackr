from datetime import datetime
from datetime import timedelta
from typing import Any, Dict

import os
import jwt as pyjwt
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

# Load env vars from root directory (parent of backend)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
load_dotenv(os.path.join(root_dir, '.env'))

from app.routes.evaluations_v2 import program_evaluations_bp
from app.routes.chat import chat_bp
from app.services.auth_tokens import decode_app_token_from_request, issue_app_token
from app.services.evaluation_service import has_program_evaluation
from app.services.supabase_client import supabase_request

app = Flask(__name__)
CORS(app)


def build_preferences(email: str) -> Dict[str, Any]:
    # Fetch user_preferences from DB
    # First get user_id
    user_resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
    prefs = {
        'theme': 'dark',
        'landingView': 'dashboard',
        'hasProgramEvaluation': has_program_evaluation(email),
        'onboardingComplete': False
    }
    
    if user_resp.status_code == 200 and user_resp.json():
        user_id = user_resp.json()[0]['id']
        # Get prefs
        p_resp = supabase_request("GET", f"/rest/v1/user_preferences?user_id=eq.{user_id}&select=theme,landing_view,onboarding_complete")
        if p_resp.status_code == 200 and p_resp.json():
            row = p_resp.json()[0]
            prefs['theme'] = row.get('theme', 'dark')
            prefs['landingView'] = row.get('landing_view', 'dashboard')
            prefs['onboardingComplete'] = row.get('onboarding_complete', False)
            
    return prefs


def _get_redirect_url() -> str:
    is_debug = os.getenv('DEBUG', 'true').lower() == 'true'
    base_url = os.getenv('DEV_SERVER_URL') if is_debug else os.getenv('PROD_SERVER_URL')
    
    url = base_url or 'http://localhost:5173'
    if is_debug and base_url and 'localhost' in base_url and ':' not in base_url.replace('http://', '').replace('https://', ''):
        client_port = os.getenv('CLIENT_PORT', '5173')
        url = f"{base_url}:{client_port}"
    
    print(f"DEBUG: Redirect URL calculated as: {url}")
    return url


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}), 200

@app.route('/auth/sign-up', methods=['POST'])
def sign_up():
    try:
        data = request.get_json()
        email = data.get('email', '')
        password = data.get('password', '')
        stay_logged_in = bool(data.get('stayLoggedIn'))
        
        if not email.endswith('@chapman.edu'):
            return jsonify({'error': 'Use your @chapman.edu email to continue.'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters.'}), 400
        
        redirect_url = _get_redirect_url()

        supabase_payload = {
            'email': email,
            'password': password,
            'data': {
                'stay_logged_in': stay_logged_in
            },
            'options': {
                'emailRedirectTo': redirect_url
            }
        }

        response = supabase_request('POST', '/auth/v1/signup', json=supabase_payload)
        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.status_code >= 400:
            message = body.get('msg') or body.get('message') or 'Unable to create account.'
            if 'API key' in message:
                print(f"Supabase Auth Error: {response.status_code} - {message}")
                return jsonify({'error': 'Service configuration error. Please contact support.'}), 500
            return jsonify({'error': message}), response.status_code

        user = body.get('user') or {}
        confirmed = bool(user.get('email_confirmed_at'))

        if not confirmed:
            return jsonify({
                'status': 'pending_confirmation',
                'message': 'Check your email for the confirmation link to finish setting up your account.',
                'user': {'email': email}
            }), 202

        # Ensure app_user exists
        user_resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
        if user_resp.status_code != 200 or not user_resp.json():
            # Create app_user
            create_resp = supabase_request("POST", "/rest/v1/app_users", json={
                "email": email,
                "password_hash": "managed_by_supabase_auth",
                "password_salt": "managed_by_supabase_auth",
                "is_email_verified": True
            }, headers={"Prefer": "return=representation"})
            
            if create_resp.status_code >= 400:
                 print(f"Failed to create app_user: {create_resp.text}")

            # Also init preferences
            if create_resp.status_code in (200, 201) and create_resp.json():
                new_user_id = create_resp.json()[0]['id']
                supabase_request("POST", "/rest/v1/user_preferences", json={"user_id": new_user_id})

        token = issue_app_token(email, stay_logged_in)
        return jsonify({
            'token': token,
            'user': {'email': email},
            'preferences': build_preferences(email)
        }), 201
        
    except RuntimeError as config_err:
        return jsonify({'error': str(config_err)}), 500
    except requests.RequestException:
        return jsonify({'error': 'Unable to reach Supabase authentication service.'}), 502
    except Exception:
        return jsonify({'error': 'Ensure you are using a valid chapman.edu account AND do not already have an account.'}), 500

@app.route('/auth/sign-in', methods=['POST'])
def sign_in():
    try:
        data = request.get_json()
        email = data.get('email', '')
        password = data.get('password', '')
        stay_logged_in = bool(data.get('stayLoggedIn'))
        
        if not email.endswith('@chapman.edu'):
            return jsonify({'error': 'Use your @chapman.edu email to continue.'}), 400

        response = supabase_request(
            'POST',
            '/auth/v1/token?grant_type=password',
            json={'email': email, 'password': password}
        )

        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = {}
            message = body.get('msg') or body.get('error_description') or 'Incorrect email or password.'
            if 'API key' in message:
                print(f"Supabase Auth Error: {response.status_code} - {message}")
                return jsonify({'error': 'Service configuration error. Please contact support.'}), 500
            return jsonify({'error': message}), 401

        # Ensure app_user exists
        user_resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
        if user_resp.status_code != 200 or not user_resp.json():
            # Create app_user if missing (e.g. after deletion)
            create_resp = supabase_request("POST", "/rest/v1/app_users", json={
                "email": email,
                "password_hash": "managed_by_supabase_auth",
                "password_salt": "managed_by_supabase_auth",
                "is_email_verified": True
            }, headers={"Prefer": "return=representation"})
            
            if create_resp.status_code >= 400:
                 print(f"Failed to create app_user: {create_resp.text}")

            # Also init preferences
            if create_resp.status_code in (200, 201) and create_resp.json():
                new_user_id = create_resp.json()[0]['id']
                supabase_request("POST", "/rest/v1/user_preferences", json={"user_id": new_user_id})

        token = issue_app_token(email, stay_logged_in)
        return jsonify({
            'token': token,
            'user': {'email': email},
            'preferences': build_preferences(email)
        }), 200
        
    except RuntimeError as config_err:
        return jsonify({'error': str(config_err)}), 500
    except requests.RequestException:
        return jsonify({'error': 'Unable to reach Supabase authentication service.'}), 502
    except Exception:
        return jsonify({'error': 'Incorrect email or password.'}), 500


@app.route('/auth/resend-confirmation', methods=['POST'])
def resend_confirmation():
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip()

        if not email:
            return jsonify({'error': 'Email is required.'}), 400

        supabase_request(
            'POST',
            '/auth/v1/admin/generate_link',
            json={'type': 'signup', 'email': email, 'redirectTo': _get_redirect_url()}
        )

        return jsonify({'status': 'ok'}), 200

    except RuntimeError as config_err:
        return jsonify({'error': str(config_err)}), 500
    except requests.RequestException:
        return jsonify({'error': 'Unable to reach Supabase authentication service.'}), 502
    except Exception:
        return jsonify({'error': 'Unable to resend confirmation email.'}), 500

@app.route('/auth/preferences', methods=['GET'])
def get_preferences():
    try:
        payload = decode_app_token_from_request()
        email = payload.get('email', '')
        if not email:
            return jsonify({'error': 'Invalid token'}), 401

        # Verify user still exists in DB
        user_resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
        if user_resp.status_code != 200 or not user_resp.json():
            return jsonify({'error': 'User account not found'}), 401

        return jsonify(build_preferences(email)), 200
    except pyjwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except Exception:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/auth/preferences', methods=['POST'])
def update_preferences():
    try:
        payload = decode_app_token_from_request()
        email = payload.get('email', '')
        if not email:
            return jsonify({'error': 'Invalid token'}), 401
            
        data = request.get_json() or {}
        
        # Get user_id
        user_resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
        if user_resp.status_code != 200 or not user_resp.json():
            return jsonify({'error': 'User not found'}), 404
        user_id = user_resp.json()[0]['id']
        
        # Build update payload
        update_payload = {}
        if 'theme' in data:
            update_payload['theme'] = data['theme']
        if 'landingView' in data:
            update_payload['landing_view'] = data['landingView']
        if 'onboardingComplete' in data:
            update_payload['onboarding_complete'] = bool(data['onboardingComplete'])
            
        if update_payload:
            supabase_request("PATCH", f"/rest/v1/user_preferences?user_id=eq.{user_id}", json=update_payload)
            
        return jsonify({'status': 'ok'}), 200
        
    except pyjwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except Exception:
        return jsonify({'error': 'Invalid token'}), 401


app.register_blueprint(program_evaluations_bp)
app.register_blueprint(chat_bp)

if __name__ == '__main__':
    explicit_backend_port = os.getenv('SERVER_PORT')
    port = int(explicit_backend_port or os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug_mode = os.getenv('DEBUG', 'true').lower() == 'true'
    app.run(host=host, port=port, debug=debug_mode)
