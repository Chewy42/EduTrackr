from datetime import datetime
from datetime import timedelta
from typing import Any, Dict

import os
import jwt as pyjwt
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from app.routes.program_evaluations import program_evaluations_bp
from app.services.auth_tokens import decode_app_token_from_request, issue_app_token
from app.services.program_evaluation_store import has_program_evaluation
from app.services.supabase_client import supabase_request

app = Flask(__name__)
CORS(app)


def build_preferences(email: str) -> Dict[str, Any]:
    return {
        'theme': 'dark',
        'landingView': 'dashboard',
        'hasProgramEvaluation': has_program_evaluation(email)
    }


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
            return jsonify({'error': message}), 401

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
    try:
        payload = decode_app_token_from_request()
        email = payload.get('email', '')
        if not email:
            return jsonify({'error': 'Invalid token'}), 401
        return jsonify(build_preferences(email)), 200
    except pyjwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except Exception:
        return jsonify({'error': 'Invalid token'}), 401


app.register_blueprint(program_evaluations_bp)

if __name__ == '__main__':
    explicit_backend_port = os.getenv('SERVER_PORT')
    port = int(explicit_backend_port or os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug_mode = os.getenv('DEBUG', 'true').lower() == 'true'
    app.run(host=host, port=port, debug=debug_mode)
