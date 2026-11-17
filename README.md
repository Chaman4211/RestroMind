# RestroMind

**AI-Powered Restaurant Table Monitoring System**

## Overview

RestroMind is a computer-vision-based restaurant monitoring prototype. It detects and tracks people from a camera or uploaded video, estimates table occupancy using manually configured table zones, and helps staff manage table cleaning after customers leave.

The current MVP connects live camera monitoring, table status updates, cleaning alerts, and staff cleaning confirmation through a web dashboard.

## Features

- Person detection using pretrained YOLO11n.
- Person tracking using ByteTrack.
- Live browser-camera monitoring through WebSockets.
- Uploaded-video processing.
- Manual polygon-based table-zone configuration.
- Multiple table zones monitored independently from one camera.
- Table occupancy monitoring with FREE, OCCUPIED, and NEEDS_CLEANING states.
- Customer-departure detection and automatic cleaning alerts.
- Dashboard display of open cleaning alerts.
- Staff cleaning confirmation; confirmed tables return to FREE.
- Occupancy event recording.
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
- PostgreSQL, Docker Compose, Pytest, HTTPX, pytest-cov, Ruff, Oxlint.

## Table Monitoring Workflow

1. Select a camera source and start live monitoring.
2. Draw and save a polygon zone for each table in the camera preview.
3. The vision pipeline detects and tracks people.
4. A person's position is matched against the configured table zones.
5. The occupancy service updates each table's status.
6. When a customer leaves an occupied table, the table changes to NEEDS_CLEANING and a cleaning alert is created.
7. Staff clean the table and confirm the action in the dashboard.
8. The table returns to FREE and its cleaning alert is resolved.

### Table statuses

| Status | Description |
|---|---|
| FREE | Table is available. |
| OCCUPIED | A person has been detected inside the configured table zone for the required duration. |
| NEEDS_CLEANING | A previously occupied table has become vacant and requires cleaning confirmation. |

## System Architecture

```text
Browser Camera / Uploaded Video
              |
              v
         React Frontend
              |
       REST API / WebSocket
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
        Table Status / Events
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

- Python 3.11
- Node.js and npm
- Docker Compose
- Git

### 1. Clone and configure the environment

```bash
git clone https://github.com/Chaman4211/RestroMind.git
cd RestroMind
cp .env.example .env
```

Set the PostgreSQL credentials and other required values in `.env`. Do not commit this file.

### 2. Start PostgreSQL

```bash
docker compose --env-file .env -f infrastructure/docker-compose.yml up -d
```

### 3. Set up and start the backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Backend: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

### 4. Set up and start the frontend

Open another terminal:

```bash
cd RestroMind/frontend
npm install
npm run dev
```

The frontend normally runs at http://localhost:5173. If both local RestroMind HTTPS certificate files are available under `~/.config/restromind/certs/`, Vite uses HTTPS; otherwise it starts without local HTTPS certificates.

## Testing

Run backend tests from the `backend` directory:

```bash
python -m pytest
python -m ruff check app tests
```

Run frontend checks from the `frontend` directory:

```bash
npm run lint
npm run build
```

The live monitoring and cleaning-alert implementation passed the backend test suite (67 tests), frontend lint, and frontend production build in CI at the time of its merge.

## Current Scope and Limitations

- Table zones are configured manually using polygon drawing.
- Occupancy is estimated using detected person positions inside configured zones.
- YOLO11n is used for person detection; automatic restaurant-table recognition is not implemented.
- Multiple zones can be monitored independently from one camera. Validation has focused on sequential occupancy scenarios; simultaneous multi-person accuracy has not been established.
- Detection quality depends on camera angle, lighting, occlusion, camera placement, and video quality.
- The current prototype has been tested with a laptop camera. Real restaurant CCTV integration still requires deployment and compatibility testing with the target camera system.
- Staff authentication and role-based access control are not yet implemented.
- Cleaning alerts support the table-cleaning workflow; tissue/spoon requests and advanced hygiene monitoring are outside the current MVP scope.

## Development Workflow

1. Create a GitHub issue.
2. Create a feature branch from `main`.
3. Implement and test changes.
4. Push the feature branch.
5. Open a Pull Request.
6. Review changes and automated checks.
7. Merge the approved PR into `main`.

## Contributors

- Chaman Afzaal
- Muhammad Abbas

## Project Status

**Core live table-monitoring and cleaning-alert MVP implemented.**

The current implementation supports live camera monitoring, manually configured table zones, occupancy status updates, automatic cleaning alerts, and staff cleaning confirmation. Further work can focus on testing with real restaurant CCTV footage, improving detection reliability, and adding additional restaurant operations features.
