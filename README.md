# Automated Study Planner - Flask Web App (Chunk 1-3)

## Overview
A comprehensive study planner application with both CLI and Web interfaces. Features persistent JSON storage, deadline tracking, and intelligent study plan generation with color-coded priority visualization.

## Features
- ✅ Add courses with difficulty levels (1-5)
- ✅ Add deadlines for courses (Exam, Assignment, Quiz, Project)
- ✅ Automatically generate personalized study plans
- ✅ Track completion status of study sessions
- ✅ **Persistent JSON storage** - Data automatically saved and restored
- ✅ **Cross-session state** - All data persists across application restarts
- ✅ **Flask Web Interface** - Beautiful, responsive web UI with Bootstrap 5
- ✅ **Color-coded deadlines** - Visual priority system (Red ≤3 days, Yellow ≤7 days, Green >7 days)
- ✅ **CLI Interface** - Command-line option still available

## Setup

### Prerequisites
- Python 3.7+

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

## Usage

### Web Application (Recommended)
Run the Flask web app:
```bash
python web_app.py
```
Then open your browser to: **http://127.0.0.1:5000**

### CLI Application
For command-line interface:
```bash
python main.py
```

### Web Interface Features
- **Dashboard** - Overview with stats cards and color-coded study sessions
- **Courses Page** - View all courses with difficulty ratings (⭐)
- **Deadlines Page** - Color-coded deadline list (Red/Yellow/Green)
- **Add Forms** - Easy-to-use forms for adding courses and deadlines
- **Study Plan Generation** - One-click generation with visual feedback
- **Session Tracking** - Mark sessions complete/incomplete with undo functionality

### CLI Menu Options (main.py)
1. **Add Course** - Input course name and difficulty level (1-5)
2. **Add Deadline** - Attach a deadline (Exam/Assignment/Quiz/Project) to a course
3. **View Courses** - Display all added courses in table format
4. **View Deadlines** - Display all added deadlines in table format
5. **Generate Study Plan** - Create a personalized study plan based on courses and deadlines
6. **View Study Plan** - Display the generated study plan
7. **Mark Session Complete** - Track completion of study sessions
8. **Exit** - Exit the application

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

## Data Model (Persistent JSON)
```python
# Stored in data/ directory:
courses.json       # {course_id: {course_id, name, difficulty_level, added_date}}
deadlines.json     # {deadline_id: {deadline_id, course_id, due_date, task_type}}
study_plans.json   # [{date, subject, task_type, duration, difficulty, completion_status}]
counters.json      # {course_counter, deadline_counter}
```

All data is automatically serialized to JSON on disk when courses, deadlines, or study plans are modified. Data is loaded on startup to restore the previous session state.

## Future Improvements (Chunks 4+)
- SQLite/PostgreSQL database migration for scalability
- User authentication and multi-user support
- Advanced scheduling algorithms (ML-based optimization)
- Email/SMS notifications and reminders
- Progress tracking and analytics dashboard
- Calendar integration (Google Calendar, Outlook)
- Mobile responsive enhancements

## Project Structure
```
automated_study_planner/
├── web_app.py           # Flask web application (NEW in Chunk 3)
├── main.py              # CLI application (original interface)
├── models.py            # Data classes and StorageManager
├── requirements.txt     # Python dependencies (tabulate, flask)
├── README.md            # This file
├── templates/           # HTML templates for Flask (NEW)
│   ├── base.html        # Base template with navbar
│   ├── index.html       # Dashboard
│   ├── courses.html     # Courses list
│   ├── add_course.html  # Add course form
│   ├── deadlines.html   # Deadlines list
│   └── add_deadline.html # Add deadline form
├── static/              # Static assets (NEW)
│   └── css/
│       └── style.css    # Custom styling
├── data/                # JSON storage (auto-created, gitignored)
│   ├── courses.json
│   ├── deadlines.json
│   ├── study_plans.json
│   └── counters.json
└── venv/                # Virtual environment (excluded from git)
```

## Development History
- **Chunk 1**: Initial CLI prototype with core functionality
- **Chunk 2**: Refactored with persistent JSON storage and dataclasses
- **Chunk 3**: Flask web application with Bootstrap UI and color-coded deadlines

## Technologies Used
- **Backend**: Python 3.7+, Flask 3.0.0
- **Frontend**: HTML5, Bootstrap 5.3, Custom CSS
- **Data Storage**: JSON (file-based persistence)
- **CLI**: tabulate (for formatted tables)

---
**Version**: 0.3.0 (Chunk 3 - Flask Web App MVP)
