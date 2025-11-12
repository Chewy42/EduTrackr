from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import jwt as pyjwt

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}), 200

@app.route('/auth/sign-up', methods=['POST'])
def sign_up():
    try:
        data = request.get_json()
        email = data.get('email', '')
        password = data.get('password', '')
        
        if not email.endswith('@chapman.edu'):
            return jsonify({'error': 'Use your @chapman.edu email to continue.'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters.'}), 400
        
        token = pyjwt.encode({
            'email': email,
            'exp': datetime.utcnow() + timedelta(days=7)
        }, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        return jsonify({
            'token': token,
            'user': {'email': email},
            'preferences': {'theme': 'dark', 'landingView': 'dashboard'}
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Unable to process request.'}), 500

@app.route('/auth/sign-in', methods=['POST'])
def sign_in():
    try:
        data = request.get_json()
        email = data.get('email', '')
        password = data.get('password', '')
        
        if not email.endswith('@chapman.edu'):
            return jsonify({'error': 'Use your @chapman.edu email to continue.'}), 400
        
        token = pyjwt.encode({
            'email': email,
            'exp': datetime.utcnow() + timedelta(days=7)
        }, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        return jsonify({
            'token': token,
            'user': {'email': email},
            'preferences': {'theme': 'dark', 'landingView': 'dashboard'}
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Unable to process request.'}), 500

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
    port = int(os.getenv('PORT', 8000))
    app.run(host='127.0.0.1', port=port, debug=True)
