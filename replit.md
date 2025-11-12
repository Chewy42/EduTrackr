# EduTrackr - Education Tracking Platform

## Overview
EduTrackr is a full-stack web application for Chapman University students to track their education and courses. The application features a React frontend with Material-UI and a Flask Python backend with JWT authentication.

## Project Architecture

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite 5
- **Styling**: Material-UI (MUI) + Tailwind CSS
- **Port**: 5000 (production-facing)
- **Features**: 
  - User authentication (sign-in/sign-up)
  - Chapman.edu email validation
  - JWT token management
  - User preferences storage

### Backend
- **Framework**: Flask (Python 3.11)
- **Port**: 8000 (internal, proxied by Vite)
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
The application runs both frontend and backend concurrently:
```bash
npm run dev
```

This starts:
- Flask backend on http://127.0.0.1:8000
- Vite frontend on http://0.0.0.0:5000

The frontend proxies `/api/*` requests to the backend.

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
- Port: `5000`
- Proxy: `/api` → `http://127.0.0.1:8000`

### Backend Configuration
- Host: `127.0.0.1` (local only, accessed via proxy)
- Port: `8000`
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
- 2025-11-12: Initial setup for Replit environment
  - Created Flask backend with auth endpoints
  - Configured Vite to run on port 5000 with backend proxy
  - Integrated frontend with real backend API calls
  - Set up unified development workflow

## User Preferences
- Requires Chapman.edu email for authentication
- Currently using stub authentication (to be connected to actual database/Supabase)
- JWT tokens stored in localStorage
