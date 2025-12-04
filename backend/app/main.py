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
from app.routes.schedule import schedule_bp
from app.services.auth_tokens import decode_app_token_from_request, issue_app_token
from app.services.evaluation_service import has_program_evaluation
from app.services.supabase_client import supabase_request

app = Flask(__name__)
CORS(app)


# ============================================================================
# Global Error Handlers and Request Validation
# ============================================================================

def _make_json_error(message: str, status_code: int, error_type: str = None):
    """Create a standardized JSON error response."""
    response_data = {
        'error': message,
        'status_code': status_code
    }
    if error_type:
        response_data['type'] = error_type
    response = jsonify(response_data)
    response.status_code = status_code
    return response


@app.errorhandler(400)
def handle_bad_request(error):
    """Handle 400 Bad Request errors."""
    message = str(error.description) if hasattr(error, 'description') and error.description else 'Bad request'
    return _make_json_error(message, 400, 'bad_request')


@app.errorhandler(404)
def handle_not_found(error):
    """Handle 404 Not Found errors."""
    return _make_json_error('The requested resource was not found', 404, 'not_found')


@app.errorhandler(405)
def handle_method_not_allowed(error):
    """Handle 405 Method Not Allowed errors."""
    return _make_json_error('Method not allowed', 405, 'method_not_allowed')


@app.errorhandler(422)
def handle_unprocessable_entity(error):
    """Handle 422 Unprocessable Entity errors."""
    message = str(error.description) if hasattr(error, 'description') and error.description else 'Unprocessable entity'
    return _make_json_error(message, 422, 'unprocessable_entity')


@app.errorhandler(500)
def handle_internal_error(error):
    """Handle 500 Internal Server errors."""
    print(f"Internal server error: {error}")
    return _make_json_error('Internal server error', 500, 'internal_error')


@app.errorhandler(502)
def handle_bad_gateway(error):
    """Handle 502 Bad Gateway errors."""
    return _make_json_error('Bad gateway - upstream service unavailable', 502, 'bad_gateway')


@app.errorhandler(503)
def handle_service_unavailable(error):
    """Handle 503 Service Unavailable errors."""
    return _make_json_error('Service temporarily unavailable', 503, 'service_unavailable')


@app.errorhandler(Exception)
def handle_unhandled_exception(error):
    """Catch-all handler for unhandled exceptions."""
    print(f"Unhandled exception: {type(error).__name__}: {error}")
    return _make_json_error('An unexpected error occurred', 500, 'unhandled_exception')


@app.before_request
def validate_json_content():
    """Validate JSON parsing for requests with JSON content type."""
    if request.method == 'OPTIONS':
        return None
    if request.content_type and 'application/json' in request.content_type:
        if request.content_length and request.content_length > 0:
            try:
                request.get_json(force=False, silent=False)
            except Exception:
                return _make_json_error('Invalid JSON in request body', 400, 'invalid_json')
    return None


@app.after_request
def ensure_cors_on_errors(response):
    """Ensure CORS headers are present on all responses including errors."""
    if 'Access-Control-Allow-Origin' not in response.headers:
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


# ============================================================================
# Helper Functions
# ============================================================================

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

@app.route('/health/config', methods=['GET'])
def health_config():
    """Diagnostic endpoint to check if required env vars are configured (does not expose values)."""
    from app.services.supabase_client import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'supabase_url_set': bool(SUPABASE_URL),
        'supabase_anon_key_set': bool(SUPABASE_ANON_KEY),
        'supabase_service_key_set': bool(SUPABASE_SERVICE_KEY),
        'jwt_secret_is_default': os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production") == "dev-secret-key-change-in-production",
        'debug_mode': os.getenv('DEBUG', 'true').lower() == 'true',
    }), 200

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
        print(f"Sign-in RuntimeError: {config_err}")
        return jsonify({'error': str(config_err)}), 500
    except requests.RequestException as req_err:
        print(f"Sign-in RequestException: {req_err}")
        return jsonify({'error': 'Unable to reach Supabase authentication service.'}), 502
    except Exception as e:
        print(f"Sign-in unexpected error: {type(e).__name__}: {e}")
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

        # Build update payload for user_preferences
        update_payload = {}
        if 'theme' in data:
            update_payload['theme'] = data['theme']
        if 'landingView' in data:
            update_payload['landing_view'] = data['landingView']
        if 'onboardingComplete' in data:
            update_payload['onboarding_complete'] = bool(data['onboardingComplete'])

        if update_payload:
            supabase_request("PATCH", f"/rest/v1/user_preferences?user_id=eq.{user_id}", json=update_payload)

        # If onboardingAnswers provided, save to scheduling_preferences
        if 'onboardingAnswers' in data:
            answers = data['onboardingAnswers']
            _save_onboarding_to_scheduling_preferences(user_id, answers)

        return jsonify({'status': 'ok'}), 200

    except pyjwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except Exception as e:
        print(f"Error updating preferences: {e}")
        return jsonify({'error': 'Invalid token'}), 401


def _save_onboarding_to_scheduling_preferences(user_id: str, answers: Dict[str, Any]) -> None:
    """
    Map onboarding answers to scheduling_preferences table fields.
    """
    # Build scheduling preferences payload from onboarding answers
    sched_payload = {
        "user_id": user_id,
        "updated_at": datetime.utcnow().isoformat()
    }
    collected_fields = []

    # Map planning_mode
    if 'planning_mode' in answers:
        sched_payload['planning_mode'] = answers['planning_mode']
        collected_fields.append('planning_mode')

    # Map credit_load to preferred_credits_min/max
    credit_map = {
        'light': (9, 12),
        'standard': (12, 15),
        'heavy': (15, 18)
    }
    if 'credit_load' in answers and answers['credit_load'] in credit_map:
        min_cr, max_cr = credit_map[answers['credit_load']]
        sched_payload['preferred_credits_min'] = min_cr
        sched_payload['preferred_credits_max'] = max_cr
        collected_fields.append('credits')

    # Map schedule_preference to preferred_time_of_day
    time_map = {
        'mornings': 'morning',
        'afternoons': 'afternoon',
        'flexible': 'flexible'
    }
    if 'schedule_preference' in answers and answers['schedule_preference'] in time_map:
        sched_payload['preferred_time_of_day'] = time_map[answers['schedule_preference']]
        collected_fields.append('time_preference')

    # Map work_status
    if 'work_status' in answers:
        sched_payload['work_status'] = answers['work_status']
        collected_fields.append('work_status')

    # Map priority to priority_focus
    priority_map = {
        'major': 'major_requirements',
        'electives': 'electives',
        'graduate': 'graduation_timeline'
    }
    if 'priority' in answers and answers['priority'] in priority_map:
        sched_payload['priority_focus'] = priority_map[answers['priority']]
        collected_fields.append('focus')

    sched_payload['collected_fields'] = collected_fields

    # Upsert to scheduling_preferences
    existing_resp = supabase_request("GET", f"/rest/v1/scheduling_preferences?user_id=eq.{user_id}&select=id")
    if existing_resp.status_code == 200 and existing_resp.json():
        # Update existing
        supabase_request("PATCH", f"/rest/v1/scheduling_preferences?user_id=eq.{user_id}", json=sched_payload)
    else:
        # Insert new
        supabase_request("POST", "/rest/v1/scheduling_preferences", json=sched_payload)


@app.route('/auth/scheduling-preferences', methods=['GET'])
def get_scheduling_preferences_endpoint():
    """Get the user's current scheduling preferences (from onboarding)."""
    try:
        payload = decode_app_token_from_request()
        email = payload.get('email', '')
        if not email:
            return jsonify({'error': 'Invalid token'}), 401

        # Get user_id
        user_resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
        if user_resp.status_code != 200 or not user_resp.json():
            return jsonify({'error': 'User not found'}), 404
        user_id = user_resp.json()[0]['id']

        # Get scheduling preferences
        prefs_resp = supabase_request("GET", f"/rest/v1/scheduling_preferences?user_id=eq.{user_id}&select=*")
        if prefs_resp.status_code == 200 and prefs_resp.json():
            prefs = prefs_resp.json()[0]
            # Map back to frontend format
            result = {
                'planning_mode': prefs.get('planning_mode'),
                'credit_load': _reverse_credit_map(prefs.get('preferred_credits_min'), prefs.get('preferred_credits_max')),
                'schedule_preference': _reverse_time_map(prefs.get('preferred_time_of_day')),
                'work_status': prefs.get('work_status'),
                'priority': _reverse_priority_map(prefs.get('priority_focus'))
            }
            return jsonify(result), 200
        
        return jsonify({}), 200

    except pyjwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except Exception as e:
        print(f"Error getting scheduling preferences: {e}")
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/auth/scheduling-preferences', methods=['PATCH'])
def update_scheduling_preferences_endpoint():
    """Update the user's scheduling preferences."""
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

        # Build update payload using the same mapping as onboarding
        sched_payload = {
            "updated_at": datetime.utcnow().isoformat()
        }

        # Map planning_mode
        if 'planning_mode' in data and data['planning_mode']:
            sched_payload['planning_mode'] = data['planning_mode']

        # Map credit_load to preferred_credits_min/max
        credit_map = {
            'light': (9, 12),
            'standard': (12, 15),
            'heavy': (15, 18)
        }
        if 'credit_load' in data and data['credit_load'] in credit_map:
            min_cr, max_cr = credit_map[data['credit_load']]
            sched_payload['preferred_credits_min'] = min_cr
            sched_payload['preferred_credits_max'] = max_cr

        # Map schedule_preference to preferred_time_of_day
        time_map = {
            'mornings': 'morning',
            'afternoons': 'afternoon',
            'flexible': 'flexible'
        }
        if 'schedule_preference' in data and data['schedule_preference'] in time_map:
            sched_payload['preferred_time_of_day'] = time_map[data['schedule_preference']]

        # Map work_status
        if 'work_status' in data and data['work_status']:
            sched_payload['work_status'] = data['work_status']

        # Map priority to priority_focus
        priority_map = {
            'major': 'major_requirements',
            'electives': 'electives',
            'graduate': 'graduation_timeline'
        }
        if 'priority' in data and data['priority'] in priority_map:
            sched_payload['priority_focus'] = priority_map[data['priority']]

        # Check if row exists
        existing_resp = supabase_request("GET", f"/rest/v1/scheduling_preferences?user_id=eq.{user_id}&select=id")
        if existing_resp.status_code == 200 and existing_resp.json():
            # Update existing
            supabase_request("PATCH", f"/rest/v1/scheduling_preferences?user_id=eq.{user_id}", json=sched_payload)
        else:
            # Insert new with user_id
            sched_payload['user_id'] = user_id
            supabase_request("POST", "/rest/v1/scheduling_preferences", json=sched_payload)

        return jsonify({'status': 'ok'}), 200

    except pyjwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except Exception as e:
        print(f"Error updating scheduling preferences: {e}")
        return jsonify({'error': 'Failed to update preferences'}), 500


def _reverse_credit_map(min_credits: int | None, max_credits: int | None) -> str | None:
    """Map credits back to the onboarding value."""
    if min_credits == 9 and max_credits == 12:
        return 'light'
    if min_credits == 12 and max_credits == 15:
        return 'standard'
    if min_credits == 15 and max_credits == 18:
        return 'heavy'
    return None


def _reverse_time_map(time_of_day: str | None) -> str | None:
    """Map time_of_day back to the onboarding value."""
    reverse_map = {
        'morning': 'mornings',
        'afternoon': 'afternoons',
        'flexible': 'flexible'
    }
    return reverse_map.get(time_of_day)


def _reverse_priority_map(priority_focus: str | None) -> str | None:
    """Map priority_focus back to the onboarding value."""
    reverse_map = {
        'major_requirements': 'major',
        'electives': 'electives',
        'graduation_timeline': 'graduate'
    }
    return reverse_map.get(priority_focus)


app.register_blueprint(program_evaluations_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(schedule_bp)

if __name__ == '__main__':
    explicit_backend_port = os.getenv('SERVER_PORT')
    port = int(explicit_backend_port or os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug_mode = os.getenv('DEBUG', 'true').lower() == 'true'
    app.run(host=host, port=port, debug=debug_mode)
