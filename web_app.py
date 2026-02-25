"""
Automated Study Planner - Flask Web Application
Web interface for managing courses, deadlines, and generating study plans.
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
from models import Course, Deadline, StudySession, StorageManager

app = Flask(__name__)
app.secret_key = 'study_planner_secret_key_2024'

# Initialize storage manager
storage = StorageManager()


def load_data():
    """Load all data from storage."""
    courses = storage.load_courses()
    deadlines = storage.load_deadlines()
    study_plans = storage.load_study_plans()
    counters = storage.load_counters()
    return courses, deadlines, study_plans, counters


def save_data(courses, deadlines, study_plans, counters):
    """Save all data to storage."""
    storage.save_courses(courses)
    storage.save_deadlines(deadlines)
    storage.save_study_plans(study_plans)
    storage.save_counters(counters)


def get_deadline_color(due_date_str, completion_status):
    """Calculate color based on days until deadline and completion status."""
    if completion_status:
        return 'completed'
    
    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        days_until = (due_date - today).days
        
        if days_until < 0:  # Past deadline
            return 'danger'
        elif days_until <= 3:  # 3 days or less
            return 'danger'
        elif days_until <= 7:  # 7 days or less
            return 'warning'
        else:  # More than 7 days
            return 'success'
    except ValueError:
        return 'secondary'


def generate_study_plan_logic(courses, deadlines, start_date_str=None):
    """Generate study plan based on courses and deadlines."""
    if not deadlines:
        return []
    
    if start_date_str is None:
        start_date = datetime.now().date()
    else:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = datetime.now().date()
    
    study_plans = []
    
    # Sort deadlines by due date
    sorted_deadlines = sorted(
        deadlines.items(),
        key=lambda x: datetime.strptime(x[1].due_date, "%Y-%m-%d")
    )
    
    # Generate study sessions
    for deadline_id, deadline_info in sorted_deadlines:
        course_id = deadline_info.course_id
        if course_id not in courses:
            continue
            
        course = courses[course_id]
        due_date = datetime.strptime(deadline_info.due_date, "%Y-%m-%d").date()
        
        # Calculate days until deadline
        days_until = (due_date - start_date).days
        if days_until < 0:
            continue  # Skip past deadlines
        
        # Calculate study duration based on difficulty
        difficulty = course.difficulty_level
        base_duration = 60  # minutes
        total_study_time = base_duration * difficulty
        sessions_count = max(2, difficulty)
        duration_per_session = total_study_time // sessions_count
        
        # Spread sessions across available days
        session_dates = distribute_sessions(start_date, due_date, sessions_count)
        
        for session_date in session_dates:
            study_plans.append(StudySession(
                date=session_date.strftime("%Y-%m-%d"),
                subject=course.name,
                task_type=deadline_info.task_type,
                duration=duration_per_session,
                difficulty=difficulty,
                completion_status=False
            ))
    
    # Sort by date
    study_plans.sort(key=lambda x: x.date)
    return study_plans


def distribute_sessions(start_date, end_date, num_sessions):
    """Distribute study sessions evenly between start and end dates."""
    sessions = []
    total_days = (end_date - start_date).days
    
    if total_days <= 0:
        return [start_date]
    
    interval = max(1, total_days // num_sessions)
    for i in range(num_sessions):
        session_date = start_date + timedelta(days=i * interval)
        if session_date <= end_date:
            sessions.append(session_date)
    
    # Ensure last session is on or before end date
    if sessions and sessions[-1] < end_date:
        sessions.append(end_date)
    
    return sessions


@app.route('/')
def index():
    """Dashboard - Display study plan overview."""
    courses, deadlines, study_plans, _ = load_data()
    
    # Add color coding to study plans
    for plan in study_plans:
        plan.color = get_deadline_color(plan.date, plan.completion_status)
    
    # Separate plans into upcoming and completed
    upcoming_plans = [p for p in study_plans if not p.completion_status]
    completed_plans = [p for p in study_plans if p.completion_status]
    
    return render_template(
        'index.html',
        upcoming_plans=upcoming_plans,
        completed_plans=completed_plans,
        courses=courses,
        deadlines=deadlines
    )


@app.route('/courses')
def view_courses():
    """Display all courses."""
    courses, _, _, _ = load_data()
    return render_template('courses.html', courses=courses)


@app.route('/courses/add', methods=['GET', 'POST'])
def add_course():
    """Add a new course."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        difficulty_str = request.form.get('difficulty', '3')
        
        if not name:
            flash('Course name cannot be empty.', 'danger')
            return redirect(url_for('add_course'))
        
        try:
            difficulty = int(difficulty_str)
            if not 1 <= difficulty <= 5:
                flash('Difficulty must be between 1 and 5.', 'danger')
                return redirect(url_for('add_course'))
        except ValueError:
            flash('Invalid difficulty level.', 'danger')
            return redirect(url_for('add_course'))
        
        courses, deadlines, study_plans, counters = load_data()
        
        course_counter = counters.get('course_counter', 0) + 1
        course_id = course_counter
        
        courses[course_id] = Course(
            course_id=course_id,
            name=name,
            difficulty_level=difficulty,
            added_date=datetime.now().strftime("%Y-%m-%d")
        )
        
        counters['course_counter'] = course_counter
        save_data(courses, deadlines, study_plans, counters)
        
        flash(f'Course "{name}" added successfully!', 'success')
        return redirect(url_for('view_courses'))
    
    return render_template('add_course.html')


@app.route('/deadlines')
def view_deadlines():
    """Display all deadlines."""
    courses, deadlines, _, _ = load_data()
    
    # Add course names to deadlines for display
    deadline_list = []
    today = datetime.now().date()
    
    for did, deadline in deadlines.items():
        if deadline.course_id in courses:
            try:
                due_date = datetime.strptime(deadline.due_date, "%Y-%m-%d").date()
                is_past = due_date < today
            except ValueError:
                is_past = False
            
            deadline_list.append({
                'id': did,
                'course_name': courses[deadline.course_id].name,
                'task_type': deadline.task_type,
                'due_date': deadline.due_date,
                'color': get_deadline_color(deadline.due_date, False),
                'is_past': is_past
            })
    
    # Sort by due date
    deadline_list.sort(key=lambda x: x['due_date'])
    
    return render_template('deadlines.html', deadlines=deadline_list)


@app.route('/deadlines/add', methods=['GET', 'POST'])
def add_deadline():
    """Add a new deadline."""
    courses, deadlines, study_plans, counters = load_data()
    
    if request.method == 'POST':
        course_id_str = request.form.get('course_id', '')
        due_date_str = request.form.get('due_date', '').strip()
        task_type = request.form.get('task_type', '').strip()
        
        try:
            course_id = int(course_id_str)
        except ValueError:
            flash('Invalid course selection.', 'danger')
            return redirect(url_for('add_deadline'))
        
        if course_id not in courses:
            flash('Selected course not found.', 'danger')
            return redirect(url_for('add_deadline'))
        
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
            return redirect(url_for('add_deadline'))
        
        if due_date.date() < datetime.now().date():
            flash('Due date must be in the future.', 'danger')
            return redirect(url_for('add_deadline'))
        
        if not task_type:
            flash('Task type cannot be empty.', 'danger')
            return redirect(url_for('add_deadline'))
        
        deadline_counter = counters.get('deadline_counter', 0) + 1
        deadline_id = deadline_counter
        
        deadlines[deadline_id] = Deadline(
            deadline_id=deadline_id,
            course_id=course_id,
            due_date=due_date_str,
            task_type=task_type
        )
        
        counters['deadline_counter'] = deadline_counter
        save_data(courses, deadlines, study_plans, counters)
        
        flash(f'Deadline added for {courses[course_id].name}!', 'success')
        return redirect(url_for('view_deadlines'))
    
    return render_template('add_deadline.html', courses=courses)


@app.route('/study-plan/generate', methods=['POST'])
def generate_plan():
    """Generate a new study plan."""
    courses, deadlines, _, counters = load_data()
    
    if not deadlines:
        flash('Add deadlines before generating a study plan.', 'warning')
        return redirect(url_for('index'))
    
    study_plans = generate_study_plan_logic(courses, deadlines)
    save_data(courses, deadlines, study_plans, counters)
    
    flash(f'Study plan generated with {len(study_plans)} sessions!', 'success')
    return redirect(url_for('index'))


@app.route('/study-plan/complete/<int:session_index>', methods=['POST'])
def complete_session(session_index):
    """Mark a study session as complete."""
    courses, deadlines, study_plans, counters = load_data()
    
    if 0 <= session_index < len(study_plans):
        study_plans[session_index].completion_status = True
        save_data(courses, deadlines, study_plans, counters)
        flash('Session marked as complete!', 'success')
    else:
        flash('Invalid session.', 'danger')
    
    return redirect(url_for('index'))


@app.route('/study-plan/uncomplete/<int:session_index>', methods=['POST'])
def uncomplete_session(session_index):
    """Mark a study session as incomplete."""
    courses, deadlines, study_plans, counters = load_data()
    
    if 0 <= session_index < len(study_plans):
        study_plans[session_index].completion_status = False
        save_data(courses, deadlines, study_plans, counters)
        flash('Session marked as incomplete.', 'info')
    else:
        flash('Invalid session.', 'danger')
    
    return redirect(url_for('index'))


@app.route('/deadlines/edit/<int:deadline_id>', methods=['GET', 'POST'])
def edit_deadline(deadline_id):
    """Edit an existing deadline."""
    courses, deadlines, study_plans, counters = load_data()
    
    if deadline_id not in deadlines:
        flash('Deadline not found.', 'danger')
        return redirect(url_for('view_deadlines'))
    
    if request.method == 'POST':
        due_date_str = request.form.get('due_date', '').strip()
        task_type = request.form.get('task_type', '').strip()
        
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
            return redirect(url_for('edit_deadline', deadline_id=deadline_id))
        
        if not task_type:
            flash('Task type cannot be empty.', 'danger')
            return redirect(url_for('edit_deadline', deadline_id=deadline_id))
        
        # Update deadline
        deadlines[deadline_id].due_date = due_date_str
        deadlines[deadline_id].task_type = task_type
        save_data(courses, deadlines, study_plans, counters)
        
        flash(f'Deadline updated successfully!', 'success')
        return redirect(url_for('view_deadlines'))
    
    deadline = deadlines[deadline_id]
    course = courses.get(deadline.course_id)
    
    return render_template('edit_deadline.html', 
                         deadline=deadline, 
                         deadline_id=deadline_id,
                         course=course)


@app.route('/deadlines/delete/<int:deadline_id>', methods=['POST'])
def delete_deadline(deadline_id):
    """Delete a deadline."""
    courses, deadlines, study_plans, counters = load_data()
    
    if deadline_id in deadlines:
        course_name = courses[deadlines[deadline_id].course_id].name if deadlines[deadline_id].course_id in courses else "Unknown"
        del deadlines[deadline_id]
        save_data(courses, deadlines, study_plans, counters)
        flash(f'Deadline for {course_name} deleted.', 'info')
    else:
        flash('Deadline not found.', 'danger')
    
    return redirect(url_for('view_deadlines'))


if __name__ == '__main__':
    app.run(debug=True)
