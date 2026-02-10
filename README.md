# Automated Study Planner - CLI with Persistent Storage (Chunk 1-2)

## Overview
This is the CLI application of the Automated Study Planner with persistent JSON storage. It provides a command-line interface for managing courses, deadlines, and generating personalized study plans. All data is automatically saved and restored across sessions.

## Features
- ✅ Add courses with difficulty levels (1-5)
- ✅ Add deadlines for courses (Exam, Assignment, Quiz, Project)
- ✅ Automatically generate personalized study plans
- ✅ View courses, deadlines, and study plans in table format
- ✅ Track completion status of study sessions
- ✅ **Persistent JSON storage** - Data automatically saved and restored
- ✅ **Cross-session state** - All data persists across application restarts

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

Run the CLI:
```bash
python main.py
```

### Interactive Menu Options
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

## Algorithm Notes (Chunk 1)
- Study sessions are distributed evenly across days until the deadline
- Session duration is based on course difficulty: `Base(60 min) × Difficulty Level`
- Number of sessions = `max(2, Difficulty Level)`
- Sessions are sorted chronologically

## Data Model (Persistent JSON)
```python
# Stored in data/ directory:
courses.json       # {course_id: {course_id, name, difficulty_level, added_date}}
deadlines.json     # {deadline_id: {deadline_id, course_id, due_date, task_type}}
study_plans.json   # [{date, subject, task_type, duration, difficulty, completion_status}]
counters.json      # {course_counter, deadline_counter}
```

All data is automatically serialized to JSON on disk when courses, deadlines, or study plans are modified. Data is loaded on startup to restore the previous session state.

## Future Improvements (Chunks 2+)
- SQLite database integration for persistence
- User authentication and account management
- Advanced scheduling algorithms (ML-based optimization)
- Web interface (Flask backend + HTML/CSS/JavaScript frontend)
- Notifications and reminders
- Progress tracking and analytics

## Project Structure
```
automated_study_planner/
├── main.py              # Main CLI application with persistent storage
├── models.py            # Data classes (Course, Deadline, StudySession) and StorageManager
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── data/                # JSON storage directory (auto-created)
│   ├── courses.json
│   ├── deadlines.json
│   ├── study_plans.json
│   └── counters.json
└── venv/                # Virtual environment (excluded from git)
```

## Git History
- **Chunk 1**: Initial CLI prototype with core functionality
- **Chunk 2**: Refactored with persistent JSON storage and dataclasses

---
**Version**: 0.2.0 (Chunk 2 - Persistent Storage)
