<!-- Animated header -->
<p align="center">
  <img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:101820,50:173B3F,100:2D6A5A&height=230&section=header&text=RestroMind&fontSize=64&fontColor=F4F7F5&animation=fadeIn&fontAlignY=36&desc=Restaurant%20Intelligence%20Workspace&descAlignY=58&descSize=18" alt="RestroMind animated header" />
</p>

<div align="center">

### Smarter tables. Smoother service. Clearer operations.

<p>
  <a href="https://github.com/Chaman4211/RestroMind"><img src="https://img.shields.io/badge/Project-RestroMind-173B3F?style=for-the-badge&logo=github&logoColor=white" alt="RestroMind repository" /></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/React-19-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React 19" />
  <img src="https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
</p>

<p>
  <img src="https://img.shields.io/badge/AI-YOLO%20%7C%20ByteTrack-orange?style=flat-square&logo=opencv&logoColor=white" alt="YOLO and ByteTrack" />
  <img src="https://img.shields.io/badge/Frontend-TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Tests-Pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white" alt="Pytest" />
  <img src="https://img.shields.io/badge/Code%20Quality-Ruff%20%7C%20Oxlint-5A45FF?style=flat-square" alt="Ruff and Oxlint" />
  <img src="https://img.shields.io/badge/Status-Active%20Development-2E8B57?style=flat-square" alt="Active development" />
</p>

<img src="https://readme-typing-svg.demolab.com?font=Inter&weight=600&size=19&duration=2800&pause=900&color=2D8A70&center=true&vCenter=true&width=720&lines=AI-assisted+table+occupancy+monitoring;QR+ordering+and+customer+order+tracking;Cleaning+workflows+and+staff+coordination;Restaurant+analytics%2C+rewards+and+games" alt="Animated RestroMind feature tagline" />

</div>

---

## 🌿 What is RestroMind?

**RestroMind** is an AI-assisted restaurant operations platform that brings table monitoring, digital ordering, staff workflows and business insights into one workspace.

It combines a React web application, a FastAPI backend and PostgreSQL with computer-vision components for person detection, tracking and table-occupancy estimation.

The goal is simple: help restaurant teams understand what is happening across tables, orders and service tasks without jumping between disconnected tools.

> **Project status:** Actively developed. RestroMind is a working project with tested application flows, but camera accuracy and production deployment still need validation in real restaurant environments.

## 🧭 Contents

- [Core features](#-core-features)
- [AI and table monitoring](#-ai-and-table-monitoring)
- [Customer journey](#-customer-journey)
- [Business analytics](#-business-analytics)
- [Architecture](#-architecture)
- [Technology stack](#-technology-stack)
- [Repository structure](#-repository-structure)
- [Run locally](#-run-locally)
- [Demo mode](#-public-demo-mode)
- [API modules](#-api-modules)
- [Tests and quality checks](#-tests-and-quality-checks)
- [Security notes](#-security-notes)
- [Current limitations](#-current-limitations)
- [Roadmap](#-roadmap)

## ✨ Core features

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>📊 Restaurant workspace</h3>
      <ul>
        <li>Overview of restaurant activity</li>
        <li>Table status and occupancy visibility</li>
        <li>Open alerts and service activity</li>
        <li>Cleaning task management</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>🪑 Table and camera management</h3>
      <ul>
        <li>Create and manage restaurant tables</li>
        <li>Configure table zones</li>
        <li>Connect supported camera sources</li>
        <li>Process uploaded video</li>
        <li>Estimate occupied and available tables</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>🧹 Cleaning and staff workflows</h3>
      <ul>
        <li>Cleaning-required alerts</li>
        <li>Staff task assignment</li>
        <li>Cleaning acknowledgement and confirmation</li>
        <li>Customer waiter and help requests</li>
        <li>Operational notifications</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>🍽️ Digital menu and ordering</h3>
      <ul>
        <li>QR-accessible customer menu</li>
        <li>Menu items, sizes and ingredients</li>
        <li>Order customization and shared-table ordering</li>
        <li>Public order tracking</li>
        <li>Order cancellation and customer feedback</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>💳 Payment tracking</h3>
      <ul>
        <li>Cash and supported digital payment-method selection</li>
        <li>Payment-request tracking</li>
        <li>Staff payment confirmation</li>
        <li>Paid and outstanding order visibility</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>📈 Business analytics</h3>
      <ul>
        <li>Daily, monthly, yearly and custom date ranges</li>
        <li>Confirmed revenue and outstanding balances</li>
        <li>Average order value and sales trends</li>
        <li>Payment breakdowns</li>
        <li>PDF and CSV report exports</li>
        <li>Restaurant name and currency settings</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>🎁 Visitor rewards</h3>
      <ul>
        <li>Customer reward experience</li>
        <li>Reward tracking and claims</li>
        <li>Rewards available in the post-order customer experience</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>🎮 Customer games and Wi-Fi</h3>
      <ul>
        <li>Invitation-based Tic-Tac-Toe</li>
        <li>Invitation-based Connect Four</li>
        <li>Restaurant Wi-Fi details for customers</li>
        <li>Encrypted storage for Wi-Fi credentials</li>
      </ul>
    </td>
  </tr>
</table>

## 🤖 AI and table monitoring

RestroMind uses a computer-vision workflow to estimate whether configured restaurant table zones are occupied.

<p align="center">
  <img src="https://img.shields.io/badge/YOLO-Person%20Detection-F28C28?style=for-the-badge" alt="YOLO person detection" />
  <img src="https://img.shields.io/badge/ByteTrack-Object%20Tracking-2878B5?style=for-the-badge" alt="ByteTrack tracking" />
  <img src="https://img.shields.io/badge/OpenCV-Video%20Processing-3B8C55?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV video processing" />
</p>

~~~mermaid
flowchart TD
    A["📹 Camera source or uploaded video"] --> B["🎞️ Frame processing"]
    B --> C["🤖 YOLO person detection"]
    C --> D["🔎 ByteTrack object tracking"]
    D --> E["📍 Match tracked positions to table zones"]
    E --> F["🪑 Estimate table occupancy"]
    F --> G{"Table state"}
    G -->|"People present"| H["🔴 Occupied"]
    G -->|"Vacated after use"| I["🧹 Cleaning required"]
    G -->|"Available"| J["🟢 Free"]
    I --> K["👨‍🍳 Staff completes cleaning"]
    K --> L["✅ Cleaning confirmed"]
    L --> J
~~~

### Monitoring flow

1. Add a supported camera source or provide a video for processing.
2. Configure table zones on the camera view.
3. Detect people in video frames.
4. Track detections across frames.
5. Match tracked positions against table zones.
6. Update the estimated table state.
7. Create a cleaning task when the workflow identifies a table that needs cleaning.
8. Staff acknowledge and confirm the cleaning task.

**Important:** Computer vision provides an estimate, not a guarantee. Camera angle, lighting, occlusion, image quality and zone placement can affect results. Real-site calibration is required.

## 🛍️ Customer journey

The customer-facing flow is designed to work from a restaurant QR menu without requiring a visitor to create an account.

~~~mermaid
flowchart TD
    A["📱 Scan table QR code"] --> B["🍽️ Browse digital menu"]
    B --> C["🛒 Customize and place order"]
    C --> D["🧾 Open order tracking"]
    D --> E["📍 Track order status"]
    D --> F["🙋 Call waiter or request help"]
    D --> G["📶 View restaurant Wi-Fi"]
    D --> H["🎁 Rewards and games"]
    E --> I["💳 Select payment method"]
    I --> J["👨‍💼 Staff confirms received payment"]
~~~

The customer tracking experience includes **Order Tracking**, **Call Waiter / Help**, **Wi-Fi**, and **Rewards & Games**.

## 📈 Business analytics

The analytics workspace helps restaurant operators review order and payment activity across selected periods.

| Metric | Meaning |
|---|---|
| Confirmed revenue | Orders marked as paid |
| Outstanding | Amount still pending or unpaid |
| Average order value | Average order amount for the selected period |
| Sales trend | Order and revenue movement over time |
| Payment breakdown | Recorded payment methods and statuses |

**Payment accuracy note:** Selecting a digital payment method does not itself verify a bank or wallet transaction. Payment confirmation is handled by authorized staff in the current implementation. RestroMind does not claim automatic payment-gateway verification.

## 🏗️ Architecture

~~~mermaid
flowchart TB
    CUSTOMER["📱 Customer"] --> WEB["⚛️ React + TypeScript"]
    STAFF["👨‍🍳 Restaurant staff"] --> WEB
    WEB <-->|"HTTP API"| API["⚡ FastAPI"]
    API <--> DB[("🐘 PostgreSQL")]
    API --> ORDERS["🍽️ Ordering and payments"]
    API --> OPS["🪑 Tables, alerts and staff"]
    API --> ANALYTICS["📈 Business analytics"]
    API --> GAMES["🎮 Rewards and games"]
    API --> CAMERA["📹 Camera and video services"]
    CAMERA --> CV["🤖 Computer vision"]
    CV --> DETECT["YOLO detection"]
    DETECT --> TRACK["ByteTrack tracking"]
    TRACK --> ZONES["📍 Table-zone matching"]
    ZONES --> OPS
~~~

## 🧰 Technology stack

<div align="center">
  <img src="https://skillicons.dev/icons?i=python,fastapi,postgres,react,ts,vite,tailwind,docker,git,github" alt="Technology stack icons" />
</div>

| Area | Tools |
|---|---|
| Frontend | React 19, TypeScript, Vite |
| Styling and icons | Tailwind CSS, Lucide React |
| Data and charts | TanStack Query, Recharts |
| Customer QR | qrcode.react |
| Backend | Python, FastAPI |
| Database and ORM | PostgreSQL, SQLAlchemy |
| Database migrations | Alembic |
| Computer vision | Ultralytics YOLO, ByteTrack, OpenCV |
| Authentication and encryption | JWT, Cryptography |
| Testing | Pytest, HTTPX |
| Code quality | Ruff, Oxlint |
| Local infrastructure | Docker Compose |

## 📂 Repository structure

~~~text
RestroMind/
├── backend/
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── scripts/
│   ├── tests/
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   └── services/
│   ├── package.json
│   └── package-lock.json
├── infrastructure/
│   └── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
~~~

## 🚀 Run locally

### Prerequisites

- Git
- Python 3.11 or newer
- Node.js and npm
- Docker with the Docker Compose plugin

### 1. Clone the repository

~~~bash
git clone https://github.com/Chaman4211/RestroMind.git
cd RestroMind
~~~

### 2. Configure environment variables

~~~bash
cp .env.example .env
openssl rand -hex 32
~~~

Set your own values in `.env` for the database password, `JWT_SECRET_KEY` and `OWNER_SETUP_KEY`. Use separate random values for the JWT secret and owner setup key. Keep `.env` private and never commit it.

The example environment file also includes `FRONTEND_URL`, `DEMO_MODE` and the optional `RTSP_ENCRYPTION_KEY`.

### 3. Start PostgreSQL

From the repository root:

~~~bash
docker compose --env-file .env -f infrastructure/docker-compose.yml up -d
docker compose --env-file .env -f infrastructure/docker-compose.yml ps
~~~

### 4. Install and start the backend

~~~bash
cd backend

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
~~~

Backend: [http://127.0.0.1:8000](http://127.0.0.1:8000)  
API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 5. Install and start the frontend

Open a second terminal from the repository root:

~~~bash
cd frontend
npm install
npm run dev
~~~

Frontend: [http://localhost:5173](http://localhost:5173)

Make sure `FRONTEND_URL` in the backend environment matches the frontend origin you use.

## 🌐 Public demo mode

RestroMind includes a demo mode intended for a public, no-signup/no-login visitor experience.

Set the following in the backend environment for the demo deployment:

~~~env
DEMO_MODE=true
~~~

For a normal protected installation:

~~~env
DEMO_MODE=false
~~~

**Deploy public demos with a separate demo database and non-production credentials.** Do not connect a public demo to a private development or production database. Keep secrets, camera credentials and private customer information out of demo data.

## 🔌 API modules

The backend API is organized under the `/api/v1` prefix.

| Module | Responsibility |
|---|---|
| Health | Basic API health endpoint |
| Authentication | Owner setup, login and demo session |
| Notifications and alerts | Operational notifications and alerts |
| Camera sources and streams | Camera source configuration and stream handling |
| Video processing | Uploaded video processing |
| Restaurant tables | Table configuration and occupancy state |
| Staff | Staff records and assignments |
| Ordering | Menus, customer orders and payment tracking |
| Service requests | Customer help and waiter requests |
| Rewards | Visitor rewards and claims |
| Games and invitations | Customer games and multiplayer invitations |
| Analytics | Business reports and restaurant profile settings |
| Wi-Fi | Restaurant Wi-Fi settings |

Use the interactive API documentation at `/docs` to inspect available routes and schemas.

## 🧪 Tests and quality checks

Run these commands from the repository root.

**Backend tests**

~~~bash
cd backend
.venv/bin/pytest -q
~~~

**Backend lint**

~~~bash
.venv/bin/ruff check app tests alembic
~~~

**Frontend lint and production build**

~~~bash
cd frontend
npm run lint
npm run build
~~~

## 🗄️ Database migrations

Check the current migration revision:

~~~bash
cd backend
.venv/bin/alembic current
.venv/bin/alembic heads
~~~

Apply migrations:

~~~bash
.venv/bin/alembic upgrade head
~~~

For an important database, plan and verify a backup before applying schema changes.

## 🔐 Security notes

- Never commit `.env`, passwords, tokens or private keys.
- Use strong, unique values for JWT and owner setup secrets.
- Keep PostgreSQL private; do not expose the database port publicly without a deliberate security design.
- Protect RTSP camera URLs and credentials.
- Keep Wi-Fi credentials encrypted and out of public API responses.
- Restrict CORS to the intended frontend origin.
- Use a separate database and safe sample data for public demos.
- Review authentication, authorization, file uploads and camera endpoints before production deployment.

## 🚧 Current limitations

RestroMind is still under active development. The following points should be considered before a real restaurant rollout:

- Occupancy is estimated and depends on camera placement, lighting, occlusion and zone configuration.
- Table zones require configuration and real-camera calibration.
- Camera compatibility must be validated with the actual target devices and network.
- Digital payment methods are recorded, but gateway-side payment verification is not integrated; staff confirmation is used.
- Analytics reports order and payment activity; profit reporting requires cost and expense data that is not currently part of the reporting model.
- Advanced hygiene sensing, inventory integrations and multi-restaurant SaaS management are not presented as completed features.

## 🗺️ Roadmap

- [x] Restaurant dashboard and table management
- [x] Customer QR menu and order tracking
- [x] Cleaning tasks, alerts and staff workflows
- [x] Visitor rewards and invitation-based customer games
- [x] Business analytics with PDF and CSV exports
- [x] YOLO / ByteTrack computer-vision workflow
- [ ] More real-camera testing and occupancy calibration
- [ ] Production deployment hardening and monitoring
- [ ] Inventory and cost tracking
- [ ] Advanced restaurant hygiene workflows
- [ ] Multi-restaurant SaaS capabilities

## 👨‍💻 Maintainer

<div align="center">
  <a href="https://github.com/Chaman4211">
    <img src="https://img.shields.io/badge/GitHub-Chaman4211-181717?style=for-the-badge&logo=github&logoColor=white" alt="Chaman Afzaal on GitHub" />
  </a>
  <br />
  <strong>Chaman Afzaal</strong>
  <br />
  Software Engineering Graduate
</div>

---

<div align="center">
  <strong>🍽️ RestroMind — Bringing intelligence to restaurant operations.</strong>
  <br />
  <sub>Built with curiosity, code and a focus on practical restaurant workflows.</sub>
  <br /><br />
  <img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:2D6A5A,50:173B3F,100:101820&height=110&section=footer" alt="Animated footer wave" />
</div>
