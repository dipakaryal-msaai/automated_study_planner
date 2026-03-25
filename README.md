# Automated Study Planner - Flask Web App (Chunk 1-6)

## Overview
A comprehensive study planner application with both CLI and Web interfaces. Features persistent SQLite/PostgreSQL database storage, deadline tracking, intelligent study plan generation, and lightweight daily outbound reminders for authenticated web users.

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

## Future Improvements (Chunks 6+)
- Advanced scheduling algorithms (ML-based optimization)
- Calendar integration (Google Calendar, Outlook)
- Progress tracking and analytics dashboard
- Mobile responsive enhancements
- REST API endpoints for mobile apps

## Project Structure
```
automated_study_planner/
├── web_app.py           # Flask web application (Chunk 3)
├── notification_worker.py # Standalone daily notification worker (Chunk 6)
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
│   └── edit_deadline.html # Edit deadline form
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
- **Chunk 5**: Authentication system (register/login/logout, multi-user data isolation, guest mode)
- **Chunk 6**: Daily summary notifications for authenticated web users

## Technologies Used
- **Backend**: Python 3.7+, Flask 3.0.0, SQLAlchemy 2.0.25, Flask-Login 0.6.3
- **Database**: SQLite (development), PostgreSQL (production)
- **Frontend**: HTML5, Bootstrap 5.3, Custom CSS
- **CLI**: tabulate (for formatted tables)
- **ORM**: SQLAlchemy with declarative models

---
**Version**: 0.6.0 (Chunk 6 - Daily Summary Notifications)
