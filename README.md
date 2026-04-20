# Automated Study Planner - Flask Web App (Chunk 1-14)

## Overview
A comprehensive study planner application with both CLI and web interfaces. Features persistent SQLite/PostgreSQL database storage, deadline tracking, intelligent study plan generation, authentication, analytics, daily reminders, an admin dashboard, session-authenticated REST API support, an in-app help guide, optional AI study insights, optional AI-assisted schedule optimization, AI reliability improvements, and AI study chat backed by local Ollama.

## Features
- ✅ Add courses with difficulty levels (1-5)
- ✅ Add deadlines for courses (Exam, Assignment, Quiz, Project)
- ✅ Automatically generate personalized study plans
- ✅ Track completion status of study sessions
- ✅ **SQLite Database Storage** - Robust database with CRUD operations (Chunk 4)
- ✅ **PostgreSQL Support** - Production-ready for Heroku deployment (Chunk 4)
- ✅ **Migration Tool** - Easy JSON-to-SQLite data migration (Chunk 4)
- ✅ **Cross-session state** - All data persists across application restarts
- ✅ **Flask Web Interface** - Beautiful, responsive web UI with Bootstrap 5
- ✅ **Color-coded deadlines** - Visual priority system (Red ≤3 days, Yellow ≤7 days, Green >7 days)
- ✅ **CLI Interface** - Command-line option still available
- ✅ **User Authentication** - Register, login, logout with secure password hashing (NEW in Chunk 5)
- ✅ **Multi-user isolation** - Each user sees only their own courses, deadlines, and study plans (NEW in Chunk 5)
- ✅ **Guest Mode** - Explore all features without registering; data is session-only with clear warnings (NEW in Chunk 5)
- ✅ **Daily Summary Notifications** - Morning outbound reminders via email and optional open-source `ntfy` push (NEW in Chunk 6)
- ✅ **Progress Tracking & Analytics Dashboard** - Completion rate, study streak, per-subject breakdowns, weekly trend charts (NEW in Chunk 7)
- ✅ **Admin Dashboard** - Platform-wide overview and user activity monitoring protected by `ADMIN_EMAILS` (NEW in Chunk 8)
- ✅ **REST API Support** - Session-authenticated JSON endpoints for courses, deadlines, study sessions, and study plan generation (NEW in Chunk 9)
- ✅ **In-App Help Guide** - Public help page with app instructions, admin access notes, and REST API endpoint reference (NEW in Chunk 10)
- ✅ **AI Study Insights** - Optional dashboard insights for deadline risk, weekly priorities, and study tips via local Ollama (NEW in Chunk 11)
- ✅ **AI Schedule Optimization** - Optional AI-assisted optimization for pending study sessions with workload guardrails (NEW in Chunk 12)
- ✅ **AI Reliability Improvements** - Reused insight caching, smaller AI requests, and one automatic optimizer retry on invalid drafts (NEW in Chunk 13)
- ✅ **AI Study Chat** - Optional dashboard chat that answers planner-aware questions and keeps transcript history in the browser session (NEW in Chunk 14)

## Setup

### Prerequisites
- Python 3.7+
- SQLite (included with Python)
- PostgreSQL (optional, for production deployment)

### Installation
1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. **(Optional) Migrate existing JSON data:**
   If you have existing data from Chunk 1-3, run the migration script:
```bash
python migrate_json_to_db.py
```
   This will convert your JSON files to SQLite database format.

## Database Configuration

### SQLite (Default)
The application uses SQLite by default with the database file at `data/study_planner.db`. No additional configuration needed.

### PostgreSQL (Production)
For production deployment (e.g., Heroku):
1. Set the `DATABASE_URL` environment variable:
```bash
export DATABASE_URL=postgresql://user:password@host:5432/database
```

2. On Heroku, this is automatically set when you add the Postgres add-on:
```bash
heroku addons:create heroku-postgresql:hobby-dev
```

The application automatically detects and uses the database specified in `DATABASE_URL`.

## Usage

### Web Application (Recommended)
Run the Flask web app:
```bash
python web_app.py
```
Then open your browser to: **http://127.0.0.1:5000**

The in-app help page is available at:

```text
http://127.0.0.1:5000/help
```

To run notification delivery outside the web process:
```bash
python notification_worker.py
```

For a one-time delivery check:
```bash
python notification_worker.py --once
```

### CLI Application
For command-line interface:
```bash
python main.py
```

### REST API

The app exposes JSON endpoints under `/api/v1` for authenticated users. The API uses the same session/cookie login model as the web UI.

1. Log in through the existing web auth flow to establish a session cookie.
2. Send JSON requests to `/api/v1/...` with that cookie.
3. Read `/api/v1/auth/status` to confirm whether the current client is authenticated.

Write endpoints expect `Content-Type: application/json` and return JSON errors instead of HTML redirects.

### AI Study Insights

Chunk 11 adds an optional AI panel to the dashboard for logged-in users. It does **not** replace the planner algorithm. Instead, it reads the existing planner state and generates advisory insights:

- deadline risk summary
- weekly priorities
- study tips

The feature uses a local Ollama model and stays disabled unless explicitly enabled.

```bash
AI_INSIGHTS_ENABLED=1
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
```

Add those lines to your local `.env` file, then run Ollama separately:

```bash
ollama serve
ollama pull llama3.2
```

If you request insights again without changing your planner data, the dashboard now reuses the cached AI result instead of making another Ollama call.

### AI Schedule Optimization

Chunk 12 adds a second dashboard action: **Optimize Schedule**.

The optimizer runs only after a base plan exists. It can adjust:

- pending session dates
- pending session durations
- the number of pending sessions

Guardrails still apply:

- completed history is preserved
- only pending sessions are replaced
- total pending planned time must remain within **+/-20%** of the base plan
- sessions cannot be scheduled in the past
- sessions cannot be scheduled after their allowed deadline window

Chunk 13 improves reliability by automatically retrying the optimizer once when the first AI draft fails server-side validation.

Optional local tuning:

```bash
OLLAMA_REQUEST_TIMEOUT_SECONDS=30
OLLAMA_JSON_RETRY_ATTEMPTS=2
OLLAMA_TEMPERATURE=0.2
```

### AI Study Chat

Chunk 14 adds a dashboard chat panel for logged-in users.

The first version is intentionally low-invasive:

- it answers questions about the current planner snapshot
- it can also give general study advice
- chat history stays only in the current browser session
- the transcript is cleared on logout or when the user clicks **Clear Chat**

#### Core Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/auth/status` | Check session auth status and current user info |
| `GET`, `POST` | `/api/v1/courses` | List or create courses |
| `GET`, `PATCH`, `DELETE` | `/api/v1/courses/<id>` | Read, update, or delete a course |
| `GET`, `POST` | `/api/v1/deadlines` | List or create deadlines |
| `GET`, `PATCH`, `DELETE` | `/api/v1/deadlines/<id>` | Read, update, or delete a deadline |
| `GET` | `/api/v1/study-sessions` | List generated study sessions |
| `PATCH` | `/api/v1/study-sessions/<id>` | Update session completion status |
| `POST` | `/api/v1/study-plan/generate` | Generate and persist a fresh study plan |

#### Example `curl` workflow

```bash
# Log in and save the Flask session cookie
curl -i -c cookies.txt \
  -X POST http://127.0.0.1:5000/auth/login \
  -d "email=you@example.com" \
  -d "password=your-password"

# Confirm auth status
curl -b cookies.txt http://127.0.0.1:5000/api/v1/auth/status

# Create a course
curl -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"name":"Calculus","difficulty_level":4}' \
  http://127.0.0.1:5000/api/v1/courses

# Generate the study plan
curl -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{}' \
  http://127.0.0.1:5000/api/v1/study-plan/generate
```

### Web Interface Features
- **Landing Page** - Redirects to Login; guests can click "Continue as guest"
- **Dashboard** - Overview with stats cards and color-coded study sessions
- **Courses Page** - View all courses with difficulty ratings (⭐)
- **Deadlines Page** - Color-coded deadline list (Red/Yellow/Green)
- **Add Forms** - Easy-to-use forms for adding courses and deadlines
- **Study Plan Generation** - One-click generation with visual feedback
- **Session Tracking** - Mark sessions complete/incomplete with undo functionality
- **Guest Mode Banner** - Persistent warning bar with link to register
- **Notification Queue** - View pending, sent, and failed daily reminders
- **Notification Settings** - Configure morning summary time and optional `ntfy` topic
- **Analytics Dashboard** - Completion rate, study hours, day streak, sessions by subject, weekly trend charts, upcoming deadlines
- **Admin Dashboard** - Platform totals, recent registration trends, and per-user activity for approved admin accounts
- **Help Page** - Public in-app guide for feature walkthroughs, guest/account behavior, admin access, and REST API usage
- **AI Insights Panel** - Optional dashboard assistant for risk summary, weekly priorities, and study tips
- **AI Schedule Optimization** - Optional dashboard action to improve the pending plan while keeping workload within guardrails
- **AI Reliability Enhancements** - Cached unchanged insights and a one-time optimizer retry to reduce flaky local-model failures
- **AI Study Chat** - Optional dashboard chat for planner-aware questions and study advice with browser-session history

### CLI Menu Options (main.py)
1. **Add Course** - Input course name and difficulty level (1-5)
2. **Add Deadline** - Attach a deadline (Exam/Assignment/Quiz/Project) to a course
3. **View Courses** - Display all added courses in table format
4. **View Deadlines** - Display all added deadlines in table format
5. **Generate Study Plan** - Create a personalized study plan based on courses and deadlines
6. **View Study Plan** - Display the generated study plan
7. **Mark Session Complete** - Track completion of study sessions
8. **Exit** - Exit the application

## Daily Notification System (Chunk 6)

Chunk 6 sends a single morning reminder on days when an authenticated user has study sessions scheduled.

- Default delivery time: `08:00`
- Default channel: account email
- Optional second channel: [`ntfy`](https://ntfy.sh/), an open-source/self-hostable push notification service
- Guest sessions do not send outbound reminders

Example reminder:

```text
Hey Dipak, you have 4 study sessions coming up today.
```

### Configuration

Email delivery uses standard SMTP environment variables:

```bash
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USERNAME=you@example.com
export SMTP_PASSWORD=your-password
export SMTP_FROM_EMAIL=you@example.com
```

Optional `ntfy` delivery uses an open-source push server:

```bash
export NTFY_SERVER=https://ntfy.sh
```

Users can configure their personal `ntfy` topic and daily summary time from the web UI under `Settings`.

### Scheduler Options

The web app includes a lightweight in-process scheduler, and a standalone worker is also available.

```bash
export NOTIFICATION_SCHEDULER_ENABLED=1
export NOTIFICATION_POLL_INTERVAL_SECONDS=60
```

- Set `NOTIFICATION_SCHEDULER_ENABLED=0` if you only want to use `notification_worker.py`
- `NOTIFICATION_POLL_INTERVAL_SECONDS` controls how often due reminders are checked

## Admin Dashboard (Chunk 8)

Chunk 8 adds a restricted admin dashboard for platform-level monitoring.

### Configuration

Grant admin access by setting a comma-separated list of email addresses:

```bash
export ADMIN_EMAILS=admin@example.com,owner@example.com
```

Only authenticated users whose email appears in `ADMIN_EMAILS` can access `/admin`.

### Example Workflow
```
1. Add Course "Calculus" (Difficulty: 4)
2. Add Course "Biology" (Difficulty: 3)
3. Add Deadline for Calculus: Exam on 2026-02-20
4. Add Deadline for Biology: Assignment on 2026-02-15
5. Generate Study Plan
6. View Study Plan
7. Mark sessions as complete as you progress
```

## Color-Coded Priority System (Chunk 3)
The web interface uses intelligent color coding for deadline visualization:
- 🔴 **Red (Danger)**: ≤ 3 days until deadline OR past deadline
- 🟡 **Yellow (Warning)**: ≤ 7 days until deadline
- 🟢 **Green (Success)**: > 7 days until deadline
- ⚪ **Gray**: Completed tasks

Colors automatically update as deadlines approach, helping you prioritize effectively.

## Study Plan Algorithm
- Study sessions are distributed evenly across days until the deadline
- Session duration is based on course difficulty: `Base(60 min) × Difficulty Level`
- Number of sessions = `max(2, Difficulty Level)`
- Sessions are sorted chronologically
- Past deadlines are automatically skipped during generation

## Data Model (SQLite/PostgreSQL Database)

### Database Schema (NEW in Chunk 4)
```sql
-- users table (NEW in Chunk 5)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATE NOT NULL
);

-- courses table
CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    difficulty_level INTEGER NOT NULL CHECK(difficulty_level >= 1 AND difficulty_level <= 5),
    added_date DATE NOT NULL,
    user_id INTEGER REFERENCES users(id)  -- NULL for legacy/pre-auth rows
);

-- deadlines table
CREATE TABLE deadlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    due_date DATE NOT NULL,
    task_type TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(id)
);

-- study_sessions table
CREATE TABLE study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    subject TEXT NOT NULL,
    task_type TEXT NOT NULL,
    duration INTEGER NOT NULL,
    difficulty INTEGER NOT NULL,
    completion_status BOOLEAN DEFAULT FALSE NOT NULL
);

-- metadata table
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### CRUD Operations
The application provides full Create, Read, Update, Delete operations for:
- **Courses**: Add, view, update difficulty, delete (with cascade to deadlines)
- **Deadlines**: Add, view, update date/type, delete
- **Study Sessions**: Generate, view, mark complete/incomplete, clear

### Previous JSON Storage (Chunk 1-3)
Legacy JSON files in `data/` directory:
- `courses.json` - Dict[int, Course] keyed by course_id
- `deadlines.json` - Dict[int, Deadline] keyed by deadline_id  
- `study_plans.json` - List[StudySession] sorted chronologically
- `counters.json` - Auto-increment IDs for courses/deadlines

**Migration**: Use `migrate_json_to_db.py` to convert JSON files to SQLite database.

## Future Improvements (Chunks 15+)
- Advanced scheduling algorithms (ML-based optimization)
- Calendar integration (Google Calendar, Outlook)
- Mobile responsive enhancements

## Project Structure
```
automated_study_planner/
├── web_app.py           # Flask web application (Chunk 3)
├── notification_worker.py # Standalone daily notification worker (Chunk 6)
├── ai_service.py         # Optional Ollama-backed AI insights, optimization, and chat service (NEW in Chunk 11-14)
├── main.py              # CLI application (original interface)
├── models.py            # Data classes (Course, Deadline, StudySession)
├── database.py          # SQLAlchemy ORM and DatabaseManager (NEW in Chunk 4)
├── migrate_json_to_db.py # JSON to SQLite migration tool (NEW in Chunk 4)
├── requirements.txt     # Python dependencies (tabulate, flask, sqlalchemy, psycopg2)
├── .env.example         # Environment variable template (NEW in Chunk 4)
├── README.md            # This file
├── templates/           # HTML templates for Flask
│   ├── base.html        # Base template with navbar
│   ├── index.html       # Dashboard
│   ├── courses.html     # Courses list
│   ├── add_course.html  # Add course form
│   ├── deadlines.html   # Deadlines list
│   ├── add_deadline.html # Add deadline form
│   ├── edit_deadline.html # Edit deadline form
│   ├── notifications.html # Notification queue
│   ├── notification_settings.html # Notification config
│   ├── analytics.html   # Progress & analytics dashboard (NEW in Chunk 7)
│   ├── admin.html       # Platform admin dashboard (NEW in Chunk 8)
│   └── help.html        # Public help and API guide (NEW in Chunk 10)
├── static/              # Static assets
│   └── css/
│       └── style.css    # Custom styling
├── data/                # Database storage (auto-created, gitignored)
│   └── study_planner.db # SQLite database (NEW in Chunk 4)
└── venv/                # Virtual environment (excluded from git)
```

## Development History
- **Chunk 1**: Initial CLI prototype with core functionality
- **Chunk 2**: Refactored with persistent JSON storage and dataclasses
- **Chunk 3**: Flask web application with Bootstrap UI and color-coded deadlines
- **Chunk 4**: SQLite/PostgreSQL database backend and JSON migration utility
- **Chunk 5**: Authentication system (register/login/logout, multi-user data isolation, guest mode)
- **Chunk 6**: Daily summary notifications for authenticated web users
- **Chunk 7**: Progress tracking & analytics dashboard (completion rate, study streak, Chart.js visualizations)
- **Chunk 8**: Admin dashboard with `ADMIN_EMAILS` access control
- **Chunk 9**: Session-authenticated REST API for core planner resources
- **Chunk 10**: Public in-app help guide with app usage and API documentation
- **Chunk 11**: Optional AI dashboard insights using a local Ollama model
- **Chunk 12**: Optional AI-assisted schedule optimization with workload guardrails
- **Chunk 13**: AI reliability improvements for cached insights and optimizer retry behavior
- **Chunk 14**: Optional dashboard AI chat with planner-aware session memory

## Technologies Used
- **Backend**: Python 3.7+, Flask 3.0.0, SQLAlchemy 2.0.25, Flask-Login 0.6.3
- **Database**: SQLite (development), PostgreSQL (production)
- **Frontend**: HTML5, Bootstrap 5.3, Chart.js 4.4, Custom CSS
- **CLI**: tabulate (for formatted tables)
- **ORM**: SQLAlchemy with declarative models

---
**Version**: 1.4.0 (Chunk 14 - AI Study Chat)
