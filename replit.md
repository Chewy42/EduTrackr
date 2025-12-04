# EduTrackr - Education Tracking Platform

## Overview
EduTrackr is a full-stack web application for Chapman University students to track their education and courses. The application features a React frontend with Material-UI and a Flask Python backend with JWT authentication.

## Project Architecture

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite 5
- **Styling**: Material-UI (MUI) + Tailwind CSS
- **Port**: 5173 (mapped to port 80 in Replit deployments)
- **Features**: 
  - User authentication (sign-in/sign-up)
  - Chapman.edu email validation
  - JWT token management
  - User preferences storage

### Backend
- **Framework**: Flask (Python 3.11)
- **Port**: 5000 (internal, proxied by Vite)
- **Features**:
  - RESTful API endpoints
  - JWT authentication
  - CORS enabled
  - Chapman.edu email domain restriction

### API Endpoints
- `GET /health` - Health check endpoint
- `POST /auth/sign-in` - User sign-in
- `POST /auth/sign-up` - User registration
- `GET /auth/preferences` - Get user preferences (requires JWT)

## Development Setup

### Running the Application
Use Replit's Run button workflows (or run the commands manually):

- **Dev** → `npm run dev` (default). Runs Flask on port 5000 and Vite on 5173.
- **DevDocker** → `npm run dev:docker`. Spins up Docker Compose, mapping host port 5173 to container port 80 so the frontend mimics the production ingress while the backend still listens on 5000.

Both options proxy `/api/*` to the backend.

### Project Structure
```
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py          # Flask application
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── auth/            # Authentication context
│   │   ├── components/      # React components
│   │   └── lib/             # API utilities
│   ├── config/
│   │   └── app.json         # Frontend config
│   ├── package.json
│   └── vite.config.ts       # Vite configuration
└── package.json             # Root package with concurrently

```

## Configuration

### Frontend Configuration
- API base URL: `/api` (proxied to backend)
- Host: `0.0.0.0` (accessible via Replit preview)
- Port: `CLIENT_PORT` env (defaults to `5173`, overridden to `80` inside Docker while still exposed on host `5173`)
- Proxy target: `VITE_PROXY_TARGET` / `SERVER_URL` (defaults to `http://127.0.0.1:5000`, set to `http://backend:5000` in Docker)

### Backend Configuration
- Host: `0.0.0.0` (bound for both local development and Replit)
- Port: `5000`
- JWT Secret: Configured via `JWT_SECRET_KEY` environment variable (defaults to dev key)

## Dependencies

### Backend (Python)
- flask - Web framework
- flask-cors - CORS support
- pyjwt - JWT token handling
- waitress - Production WSGI server
- python-dotenv - Environment variables
- requests - HTTP client
- sqlalchemy - Database ORM
- alembic - Database migrations
- psycopg - PostgreSQL adapter

### Frontend (Node.js)
- react - UI framework
- react-dom - React DOM renderer
- @mui/material - Material-UI components
- @emotion/react & @emotion/styled - CSS-in-JS
- react-icons - Icon library
- vite - Build tool
- typescript - Type safety

### Root
- concurrently - Run multiple commands concurrently

## Deployment
The application is configured for autoscale deployment on Replit, running both frontend and backend as a single service.

## Recent Changes
- 2025-12-04: Major robustness improvements to prevent crashes
  - Added global error handlers to Flask backend for all HTTP errors (400, 404, 405, 500, 502, 503)
  - Added JSON validation middleware to catch malformed requests
  - Improved Supabase client with retry logic (3 retries with exponential backoff)
  - Added React Error Boundary to prevent UI crashes from breaking the entire app
  - Improved AuthContext with health checks, token validation, and error recovery
  - Added backend_unavailable state for graceful degradation when server is down
  - Created robust API client wrapper with retry logic and timeout handling
  
- 2025-11-12: Initial setup for Replit environment
  - Created Flask backend with auth endpoints
  - Configured Vite to run on port 5173 with backend proxy
  - Integrated frontend with real backend API calls
  - Set up unified development workflow

## User Preferences
- Requires Chapman.edu email for authentication
- Currently using stub authentication (to be connected to actual database/Supabase)
- JWT tokens stored in localStorage
