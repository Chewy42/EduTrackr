from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime, timedelta
from typing import Any, Dict
import requests
import jwt as pyjwt

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
SUPABASE_URL = (os.getenv('SUPABASE_URL') or '').rstrip('/')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_ACCESS_TOKEN')


def ensure_supabase_env() -> None:
    missing = []
    if not SUPABASE_URL:
        missing.append('SUPABASE_URL')
    if not SUPABASE_ANON_KEY:
        missing.append('SUPABASE_ANON_KEY')
    if not SUPABASE_SERVICE_KEY:
        missing.append('SUPABASE_ACCESS_TOKEN')
    if missing:
        raise RuntimeError(f"Missing Supabase configuration: {', '.join(missing)}")


def supabase_headers() -> Dict[str, str]:
    return {
        'apikey': SUPABASE_ANON_KEY or '',
        'Authorization': f"Bearer {SUPABASE_SERVICE_KEY}",
        'Content-Type': 'application/json'
    }


def supabase_request(method: str, path: str, **kwargs: Any) -> requests.Response:
    ensure_supabase_env()
    url = f"{SUPABASE_URL}{path}"
    headers = kwargs.pop('headers', {})
    merged_headers = {**supabase_headers(), **headers}
    timeout = kwargs.pop('timeout', 30)
    return requests.request(method=method.upper(), url=url, headers=merged_headers, timeout=timeout, **kwargs)


def issue_app_token(email: str, stay_logged_in: bool = False) -> str:
    ttl = timedelta(days=30 if stay_logged_in else 7)
    payload = {
        'email': email,
        'exp': datetime.utcnow() + ttl
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

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
        
        supabase_payload = {
            'email': email,
            'password': password,
            'data': {
                'stay_logged_in': stay_logged_in
            }
        }

        response = supabase_request('POST', '/auth/v1/signup', json=supabase_payload)
        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.status_code >= 400:
            message = body.get('msg') or body.get('message') or 'Unable to create account.'
            return jsonify({'error': message}), response.status_code

        user = body.get('user') or {}
        confirmed = bool(user.get('email_confirmed_at'))

        if not confirmed:
            return jsonify({
                'status': 'pending_confirmation',
                'message': 'Check your email for the confirmation link to finish setting up your account.',
                'user': {'email': email}
            }), 202

        token = issue_app_token(email, stay_logged_in)
        return jsonify({
            'token': token,
            'user': {'email': email},
            'preferences': {'theme': 'dark', 'landingView': 'dashboard'}
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
            return jsonify({'error': message}), 401

        token = issue_app_token(email, stay_logged_in)
        return jsonify({
            'token': token,
            'user': {'email': email},
            'preferences': {'theme': 'dark', 'landingView': 'dashboard'}
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
            json={'type': 'signup', 'email': email}
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
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        token = auth_header.split(' ')[1]
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        return jsonify({
            'theme': 'dark',
            'landingView': 'dashboard'
        }), 200
        
    except pyjwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except Exception:
        return jsonify({'error': 'Invalid token'}), 401

if __name__ == '__main__':
    explicit_backend_port = os.getenv('SERVER_PORT')
    port = int(explicit_backend_port or os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug_mode = os.getenv('DEBUG', 'true').lower() == 'true'
    app.run(host=host, port=port, debug=debug_mode)
