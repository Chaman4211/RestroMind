# RestroMind

**AI-Powered Restaurant Table Monitoring and Management System**

## Overview

RestroMind is a computer-vision-based restaurant monitoring system. It detects and tracks people from camera streams or uploaded videos, estimates table occupancy using manually configured table zones, and helps restaurant staff manage cleaning tasks.

The current MVP combines camera monitoring, table status updates, cleaning alerts, staff management, and a web dashboard.

## Features

### Camera Monitoring
- Browser-camera live monitoring through WebSockets.
- RTSP and RTSPS IP camera sources.
- Start, stop, and check RTSP stream status.
- Uploaded-video processing.
- Camera source creation and management.

### Computer Vision
- Person detection using pretrained YOLO11n.
- Person tracking using ByteTrack.
- Video processing with OpenCV.
- Manual polygon-based table-zone configuration.
- Occupancy estimation using detected person positions within configured zones.

### Table and Cleaning Management
- Create, view, update, and delete restaurant tables.
- FREE, OCCUPIED, and NEEDS_CLEANING table states.
- Occupancy event recording.
- Automatic cleaning alerts when an occupied table becomes vacant.
- Cleaning task assignment to cleaning staff.
- Staff confirmation of completed cleaning.

### Authentication and Staff
- Initial owner account setup.
- Login using email and password.
- JWT access tokens and current-user endpoint.
- Password hashing and verification.
- Staff records, roles, and activation status.
- Role checks for protected table and alert operations.

## Technology Stack

| Area | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| UI and Data | Tailwind CSS, TanStack Query, React Router, Lucide React, Recharts |
| Backend | Python 3.11, FastAPI, Pydantic |
| Computer Vision | Ultralytics YOLO11n, ByteTrack, OpenCV |
| Database | PostgreSQL, SQLAlchemy |
| Migrations | Alembic |
| Authentication | JWT, password hashing |
| Testing | Pytest, HTTPX |
| Code Quality | Ruff, Oxlint, TypeScript |
| Infrastructure | Docker Compose |

## Table Monitoring Workflow

1. Select a browser camera, RTSP camera, or uploaded video.
2. Configure a polygon zone for each restaurant table.
3. The vision pipeline detects and tracks people in video frames.
4. Detected person positions are checked against the configured table zones.
5. The occupancy service updates the table state.
6. When a previously occupied table becomes vacant, it can be marked as NEEDS_CLEANING and a cleaning alert is created.
7. A manager can assign the cleaning task to a cleaning staff member.
8. Staff clean the table and confirm completion through the application.
9. The table returns to FREE.

### Table statuses

| Status | Description |
|---|---|
| FREE | The table is available. |
| OCCUPIED | A person is detected inside the configured table zone for the required duration. |
| NEEDS_CLEANING | A previously occupied table has become vacant and requires cleaning confirmation. |

## Architecture

```text
Browser Camera / RTSP Camera / Uploaded Video
                     |
                     v
                React Frontend
                     |
              REST API / WebSocket
                     |
                     v
                  FastAPI
                     |
             Video Processing
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
          Dashboard / Cleaning Alerts
```

## Project Structure

```text
RestroMind/
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

- Ubuntu or another supported operating system.
- Python 3.11.
- Node.js and npm.
- Docker and Docker Compose.
- Git.

### 1. Clone the repository

```bash
git clone https://github.com/Chaman4211/RestroMind.git
cd RestroMind
```

### 2. Configure environment variables

Copy the example file:

```bash
cp .env.example .env
```

The backend requires PostgreSQL credentials and a JWT secret. Owner setup and RTSP URL encryption use additional optional settings that should be configured when those features are used.

Generate secure values:

```bash
openssl rand -hex 32
openssl rand -hex 32
```

Add the generated values to `.env` as `JWT_SECRET_KEY` and `OWNER_SETUP_KEY`. Set `RTSP_ENCRYPTION_KEY` as well when using RTSP camera sources, following the encryption implementation's required key format.

Keep `.env` private. Do not commit passwords, camera URLs, or secret keys.

### 3. Start PostgreSQL

Run this command from the project root:

```bash
docker compose --env-file .env -f infrastructure/docker-compose.yml up -d
```

Check the database container:

```bash
docker compose --env-file .env -f infrastructure/docker-compose.yml ps
```

### 4. Set up the backend

Open a terminal and run:

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

Health endpoint: http://127.0.0.1:8000/api/v1/health

### 5. Set up the frontend

Open a second terminal:

```bash
cd ~/projects/restromind/frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

If the local RestroMind HTTPS certificate files are available under `~/.config/restromind/certs/`, Vite can use HTTPS. Otherwise, it starts without local HTTPS certificates.

## Camera Setup

### Browser camera
Open the live monitoring page and allow the browser to access the selected camera.

### RTSP/IP camera
1. Add a camera source with type RTSP.
2. Provide a valid RTSP or RTSPS address.
3. Configure `RTSP_ENCRYPTION_KEY` in the backend environment.
4. Start the RTSP stream using the camera controls.
5. Check the stream status in the application.

RTSP operation depends on network access, camera credentials, stream compatibility, and camera configuration. Do not expose camera credentials in screenshots, logs, or public repositories.

### Uploaded video
Select a supported video file through the video-processing workflow.

## API Overview

The API uses the `/api/v1` prefix.

| Module | Main routes |
|---|---|
| Health | `GET /health` |
| Authentication | `POST /auth/setup-owner`, `POST /auth/login`, `GET /auth/me` |
| Staff | `/staff` |
| Camera sources | `/camera-sources` |
| RTSP controls | `/camera-sources/{id}/rtsp/start`, `/stop`, `/status` |
| Video processing | `/camera-sources/{id}/process-video` |
| Restaurant tables | `/restaurant-tables` |
| Cleaning confirmation | `POST /restaurant-tables/{id}/confirm-cleaning` |
| Alerts | `/alerts` |

Open http://127.0.0.1:8000/docs for endpoint parameters, request schemas, and response details.

## Testing and Code Quality

Run backend tests from the project root:

```bash
cd backend
.venv/bin/python -m pytest
```

Run backend lint checks:

```bash
.venv/bin/python -m ruff check app tests
```

Run frontend lint and production build:

```bash
cd ~/projects/restromind/frontend
npm run lint
npm run build
```

Latest project validation reported 83 passing backend tests, clean Ruff checks, zero Oxlint warnings and errors, successful TypeScript compilation, and a successful Vite production build.

## Current Scope and Limitations

- Table zones are configured manually using polygon drawing.
- Occupancy is estimated from detected person positions; it is not a direct measurement of customer identity or intent.
- YOLO11n is used for person detection. Automatic restaurant-table recognition is not implemented.
- Detection quality depends on camera angle, lighting, occlusion, placement, and video quality.
- RTSP support is implemented, but compatibility and reliability still need validation with different real restaurant CCTV systems.
- Multi-person and multi-table accuracy needs further real-world testing.
- The current MVP focuses on table occupancy and cleaning workflows.
- Tissue/spoon requests, advanced hygiene monitoring, inventory intelligence, and POS integration are outside the current MVP scope.

## Development Workflow

1. Create or select a GitHub issue.
2. Create a feature branch from `main`.
3. Implement the change.
4. Run the relevant backend and frontend checks.
5. Push the feature branch.
6. Open a Pull Request for review.
7. Merge the approved changes into `main`.

## Contributor

- Chaman Afzaal

## Project Status

**Core restaurant table-monitoring MVP implemented.**

The current implementation includes browser-camera monitoring, RTSP/IP camera support, uploaded-video processing, table occupancy monitoring, cleaning alerts, staff management, and authentication. Further work includes validation with real restaurant CCTV systems and improving detection reliability.
