# Quick Start Guide - Flask Web App

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

4. **Data persists**
   - All data is automatically saved to JSON files
   - Close and reopen anytime - your data is safe!

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

## Stopping the Server

Press `Ctrl+C` in the terminal where Flask is running.

---

Enjoy your study planning! 🎓
