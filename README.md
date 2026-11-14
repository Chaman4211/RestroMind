# RestroMind

**AI-Powered Restaurant Table Monitoring System**

## Overview

RestroMind is a computer-vision-based restaurant monitoring prototype that detects and tracks people, estimates table occupancy, and supports table-cleaning workflows.

## Features

- Person detection using pretrained YOLO11n.
- Person tracking using ByteTrack.
- Manual polygon-based table-zone configuration.
- Table occupancy monitoring.
- FREE, OCCUPIED, and NEEDS_CLEANING states.
- Occupancy event recording and cleaning alerts.
- Staff cleaning confirmation workflow.
- Video upload processing.
- Browser-based live camera monitoring using WebSockets.
- PostgreSQL database integration.
- React operations dashboard.

## Technology Stack

### Frontend
- React, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, Lucide React, Recharts.

### Backend
- Python, FastAPI, Pydantic, SQLAlchemy, Alembic.

### Computer Vision
- Ultralytics YOLO11n, ByteTrack, OpenCV.

### Database and Testing
- PostgreSQL, Docker Compose, Pytest, HTTPX, pytest-cov, Ruff.

## Occupancy Workflow

| Status | Description |
|---|---|
| FREE | Table is available. |
| OCCUPIED | A person is detected inside the configured table zone for the required duration. |
| NEEDS_CLEANING | A previously occupied table becomes vacant and requires cleaning confirmation. |

After cleaning confirmation, the table returns to FREE.

## System Architecture

```text
Browser Camera / Uploaded Video
              |
              v
         React Frontend
              |
              v
          FastAPI API
              |
              v
      Computer Vision Pipeline
              |
       YOLO11n Detection
              |
        ByteTrack Tracking
              |
              v
        Table Zone Matching
              |
              v
      Occupancy State Machine
              |
              v
         PostgreSQL
              |
              v
       Dashboard and Alerts
```

## Project Structure

```text
restromind/
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   └── package.json
├── infrastructure/
│   └── docker-compose.yml
├── data/
├── docs/
├── .env.example
├── .gitignore
└── README.md
```

## Local Setup

### Requirements
- Python 3.11, Node.js, npm, Docker Compose, and Git.

### 1. Configure environment
```bash
cp .env.example .env
```
Set PostgreSQL credentials in `.env`.

### 2. Start PostgreSQL
```bash
docker compose --env-file .env -f infrastructure/docker-compose.yml up -d
```

### 3. Start backend
```bash
cd backend
conda activate ~/projects/restromind/backend/.venv
alembic upgrade head
uvicorn app.main:app --reload
```
Backend: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

### 4. Start frontend in another terminal
```bash
cd ~/projects/restromind/frontend
npm install
npm run dev
```
Frontend: http://localhost:5173

## Testing

Backend tests: `python -m pytest`

Code quality: `python -m ruff check app tests`

Frontend build: `npm run build`

## Current Scope and Limitations

- The vision pipeline detects and tracks people.
- Table zones are configured manually using polygon drawing.
- Occupancy is estimated using person positions inside configured zones.
- YOLO11n detects people; automatic restaurant-table recognition is not implemented.
- Detection quality depends on camera angle, lighting, occlusion, and video quality.
- Suitable restaurant footage is required for meaningful validation.
- Real CCTV integration requires deployment and compatibility testing.
- Staff authentication and role-based access control are not yet implemented.

## Development Workflow

1. Create a GitHub issue.
2. Create a feature branch from `main`.
3. Implement and test changes.
4. Push the feature branch.
5. Open a genuine Pull Request.
6. Review changes and automated checks.
7. Merge the approved PR into `main`.

## Contributors

- Chaman Afzaal
- Muhammad Abbas

## Project Status

**Active Prototype Development**

The current focus is completing the monitoring workflow, integrating the frontend and backend, and validating the system with suitable restaurant footage.
