# Quick Start Guide - Flask Web App (Updated for Chunk 4)

## First-Time Setup

### 1. Install Dependencies
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages (includes SQLAlchemy)
pip install -r requirements.txt
```

### 2. Migrate Existing Data (Optional)
If you have JSON data from Chunk 1-3:
```bash
python migrate_json_to_db.py
```
This converts your JSON files to SQLite database. Your original files are backed up as `.json.bak`.

## Starting the Web Application

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Start the Flask server:**
   ```bash
   python web_app.py
   ```

3. **Open your browser:**
   Navigate to: **http://127.0.0.1:5000**

## Using the Web Interface

### First Time Setup

1. **Add Courses**
   - Click "Courses" in navigation
   - Click "Add Course" button
   - Enter course name (e.g., "Calculus")
   - Select difficulty (1-5 stars)
   - Click "Add Course"

2. **Add Deadlines**
   - Click "Deadlines" in navigation
   - Click "Add Deadline" button
   - Select a course from dropdown
   - Choose task type (Exam/Assignment/Quiz/Project)
   - Pick a due date
   - Click "Add Deadline"

3. **Generate Study Plan**
   - Return to Dashboard (click "Dashboard" or logo)
   - Click "Generate Study Plan" button
   - View your color-coded study sessions!

### Managing Study Sessions

- **Mark as Complete**: Click green "✓ Complete" button
- **Undo**: Click "↺ Undo" button on completed sessions
- **View Status**: Colors indicate urgency
  - 🔴 Red = 3 days or less (URGENT!)
  - 🟡 Yellow = 7 days or less (Soon)
  - 🟢 Green = More than 7 days (On track)

## Features at a Glance

### Dashboard
- Quick stats cards (courses, deadlines, sessions)
- Upcoming study sessions table
- Completed sessions history
- Color legend reference

### Courses Page
- Visual cards showing all courses
- Difficulty ratings with stars
- Easy-to-scan layout

### Deadlines Page
- Table view of all deadlines
- Color-coded by urgency
- Status indicators

## Tips

1. **Higher difficulty = More study time**
   - Difficulty 1: 60 min total, 2 sessions
   - Difficulty 5: 300 min total, 5 sessions

2. **Plan ahead**
   - Add deadlines at least 2 weeks early for best results
   - The system distributes sessions evenly

3. **Track progress**
   - Mark sessions complete as you finish them
   - Watch colors update as deadlines approach

4. **Data persists automatically**
   - All data is saved to SQLite database (`data/study_planner.db`)
   - Close and reopen anytime - your data is safe!
   - No manual saving required

5. **Database advantages** (NEW in Chunk 4)
   - Faster queries and better performance
   - Data integrity with foreign keys and constraints
   - Ready for PostgreSQL deployment on Heroku

## Troubleshooting

**Port already in use?**
```bash
# Find and kill the process using port 5000
lsof -ti:5000 | xargs kill -9
```

**Dependencies missing?**
```bash
pip install -r requirements.txt
```

**Can't see CSS styling?**
- Hard refresh browser: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
- Check that static/css/style.css exists

**Migration issues?**
- Ensure JSON files are in `data/` directory
- Check migration script output for errors
- Original JSON files are backed up as `.json.bak`

## Database Information (NEW in Chunk 4)

**SQLite Location**: `data/study_planner.db`

**View database contents** (optional):
```bash
sqlite3 data/study_planner.db
.tables
SELECT * FROM courses;
.quit
```

**PostgreSQL (for Heroku deployment)**:
- Set `DATABASE_URL` environment variable
- Application automatically switches to PostgreSQL
- No code changes needed!

## Stopping the Server

Press `Ctrl+C` in the terminal where Flask is running.

---

Enjoy your study planning! 🎓
