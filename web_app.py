"""
Automated Study Planner - Flask Web Application
Web interface for managing courses, deadlines, and generating study plans.
"""

import atexit
import json
import os
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()
from threading import Event, Thread
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from database import DatabaseManager, UserModel
from models import Course, Deadline, StudySession

app = Flask(__name__)
app.secret_key = 'study_planner_secret_key_2024'

# ---------------------------------------------------------------------------
# Flask-Login setup
# ---------------------------------------------------------------------------
login_manager = LoginManager(app)
login_manager.login_view = 'auth_login'
login_manager.login_message = 'Please log in or continue as a guest to access this page.'
login_manager.login_message_category = 'info'

# Initialize database manager
db = DatabaseManager()
NOTIFICATION_POLL_INTERVAL_SECONDS = int(os.getenv('NOTIFICATION_POLL_INTERVAL_SECONDS', '60'))
_scheduler_stop_event = Event()
_scheduler_started = False


@login_manager.user_loader
def load_user(user_id: str):
    return db.get_user_by_id(int(user_id))


# ---------------------------------------------------------------------------
# Guest mode helpers  (data stored in Flask session under 'guest_*' keys)
# ---------------------------------------------------------------------------
GUEST_COURSE_CTR = 'guest_course_ctr'
GUEST_DEADLINE_CTR = 'guest_deadline_ctr'


def _guest_warn():
    flash('⚠️ Guest mode: your data will be lost when you close the browser. '
          '<a href="/auth/register" class="alert-link">Register</a> to save your progress.',
          'warning')


def _guest_courses() -> dict:
    return session.get('guest_courses', {})


def _guest_deadlines() -> dict:
    return session.get('guest_deadlines', {})


def _guest_study_plans() -> list:
    raw = session.get('guest_study_plans', [])
    return [StudySession(**s) for s in raw]


def _save_guest_courses(courses: dict) -> None:
    # Convert dataclass values to plain dicts for JSON serialisation
    session['guest_courses'] = {k: (v.to_dict() if hasattr(v, 'to_dict') else v)
                                 for k, v in courses.items()}


def _save_guest_deadlines(deadlines: dict) -> None:
    session['guest_deadlines'] = {k: (v.to_dict() if hasattr(v, 'to_dict') else v)
                                   for k, v in deadlines.items()}


def _save_guest_study_plans(plans: list) -> None:
    session['guest_study_plans'] = [
        (p.__dict__ if hasattr(p, '__dict__') else p) for p in plans
    ]


def _next_guest_id(counter_key: str) -> int:
    val = session.get(counter_key, 0) + 1
    session[counter_key] = val
    return val


# ---------------------------------------------------------------------------
# Unified data accessors — branch on authenticated vs. guest
# ---------------------------------------------------------------------------

def load_data():
    """Load all data scoped to the current user (or guest session)."""
    if current_user.is_authenticated:
        uid = current_user.id
        courses = db.get_all_courses(user_id=uid)
        deadlines = db.get_all_deadlines(user_id=uid)
        study_plans = db.get_all_study_sessions(user_id=uid)
    else:
        raw_courses = _guest_courses()
        courses = {}
        for k, v in raw_courses.items():
            if isinstance(v, dict):
                courses[int(k)] = Course(**v)
            else:
                courses[int(k)] = v

        raw_deadlines = _guest_deadlines()
        deadlines = {}
        for k, v in raw_deadlines.items():
            if isinstance(v, dict):
                deadlines[int(k)] = Deadline(**v)
            else:
                deadlines[int(k)] = v

        study_plans = _guest_study_plans()

    return courses, deadlines, study_plans


def save_study_plans(study_plans):
    """Persist study plans for the current user (or guest session).

    Completed sessions are always preserved — only incomplete sessions are
    replaced so that history is never lost on regeneration.
    """
    if current_user.is_authenticated:
        db.save_study_sessions(study_plans, user_id=current_user.id)
    else:
        # Keep completed guest sessions; replace only incomplete ones.
        existing = _guest_study_plans()
        completed = [p for p in existing if p.completion_status]
        _save_guest_study_plans(completed + study_plans)


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


def normalize_summary_time(summary_time_str):
    """Normalize a time input to HH:MM, returning None if invalid."""
    if not summary_time_str:
        return None

    try:
        return datetime.strptime(summary_time_str, "%H:%M").strftime("%H:%M")
    except ValueError:
        return None


def get_daily_summary_time(user_id=None):
    """Return the preferred summary delivery time for the requested scope."""
    return db.get_scope_setting('daily_summary_time', user_id=user_id, default='08:00')


def get_smtp_status():
    """Return SMTP configuration status for each required/optional env var."""
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = os.getenv('SMTP_PORT')
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_from_email = os.getenv('SMTP_FROM_EMAIL')

    effective_from = smtp_from_email or smtp_username
    configured = bool(smtp_host and effective_from)

    return {
        'configured': configured,
        'vars': [
            {'name': 'SMTP_HOST',       'required': True,  'set': bool(smtp_host)},
            {'name': 'SMTP_PORT',       'required': False, 'set': bool(smtp_port), 'default': '587'},
            {'name': 'SMTP_FROM_EMAIL', 'required': False, 'set': bool(smtp_from_email),
             'note': 'Required if SMTP_USERNAME is not set'},
            {'name': 'SMTP_USERNAME',   'required': False, 'set': bool(smtp_username),
             'note': 'Also used as From address when SMTP_FROM_EMAIL is absent'},
            {'name': 'SMTP_PASSWORD',   'required': False, 'set': bool(smtp_password)},
        ],
    }


def get_reset_token(email: str) -> str:
    """Generate a signed, time-limited password-reset token for the given email."""
    s = URLSafeTimedSerializer(app.secret_key)
    return s.dumps(email.lower(), salt='password-reset')


def verify_reset_token(token: str, max_age: int = 3600):
    """Return the email from a valid token, or None if expired/invalid."""
    s = URLSafeTimedSerializer(app.secret_key)
    try:
        email = s.loads(token, salt='password-reset', max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
    return email


def serialize_notifications(user_id, status=None, limit=None):
    """Shape queued notification records for template rendering."""
    if user_id is None:
        return []

    db.sync_daily_summary_reminders()
    notifications = [
        {
            'reminder_id': reminder.reminder_id,
            'summary_date': reminder.summary_date,
            'session_count': reminder.session_count,
            'greeting_name': reminder.greeting_name,
            'message': reminder.message,
            'channel': reminder.channel,
            'recipient': reminder.recipient,
            'scheduled_for': reminder.scheduled_for,
            'status': reminder.status,
            'sent_at': reminder.sent_at,
            'error_message': reminder.error_message,
        }
        for reminder in db.get_reminders(user_id=user_id, status=status)
    ]

    if limit is not None:
        notifications = notifications[:limit]
    return notifications


def run_notification_scheduler():
    """Background loop that periodically sends due notifications."""
    db.process_due_notifications()
    while not _scheduler_stop_event.wait(NOTIFICATION_POLL_INTERVAL_SECONDS):
        db.process_due_notifications()


def start_notification_scheduler():
    """Start the lightweight notification scheduler once per app process."""
    global _scheduler_started

    if _scheduler_started or os.getenv('NOTIFICATION_SCHEDULER_ENABLED', '1') == '0':
        return

    if app.debug and os.getenv('WERKZEUG_RUN_MAIN') != 'true':
        return

    scheduler_thread = Thread(
        target=run_notification_scheduler,
        name='study-session-notification-scheduler',
        daemon=True
    )
    scheduler_thread.start()
    atexit.register(_scheduler_stop_event.set)
    _scheduler_started = True


@app.context_processor
def inject_notification_summary():
    """Expose notification counts to all templates."""
    if request.endpoint == 'static' or not current_user.is_authenticated:
        return {'pending_notification_count': 0}
    return {
        'pending_notification_count': len(
            serialize_notifications(user_id=current_user.id, status='pending')
        )
    }


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


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route('/auth/register', methods=['GET', 'POST'])
def auth_register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not all([email, first_name, last_name, password]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('register.html')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        user = db.create_user(email=email, first_name=first_name,
                              last_name=last_name, password=password)
        if user is None:
            flash('An account with that email already exists.', 'danger')
            return render_template('register.html')

        login_user(user)
        flash(f'Welcome, {user.first_name}! Your account has been created.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/auth/login', methods=['GET', 'POST'])
def auth_login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        user = db.get_user_by_email(email)
        if user is None or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

        login_user(user)
        flash(f'Welcome back, {user.first_name}!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))

    return render_template('login.html')


@app.route('/auth/logout')
def auth_logout():
    logout_user()
    # Clear guest data too
    for key in ['guest_courses', 'guest_deadlines', 'guest_study_plans',
                 'guest_course_ctr', 'guest_deadline_ctr']:
        session.pop(key, None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth_login'))


@app.route('/auth/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Send a password-reset link to the user's email."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = db.get_user_by_email(email)
        if user:
            token = get_reset_token(email)
            reset_url = url_for('reset_password', token=token, _external=True)
            smtp_ok = get_smtp_status()['configured']
            if smtp_ok:
                try:
                    db._send_email(
                        recipient=email,
                        subject='Study Planner — Password Reset',
                        body=(
                            f'Hi {user.first_name},\n\n'
                            f'Click the link below to reset your password. '
                            f'This link expires in 1 hour.\n\n'
                            f'{reset_url}\n\n'
                            f'If you did not request a password reset, ignore this email.'
                        )
                    )
                except Exception:
                    pass  # Don't reveal delivery failures
        # Always show the same message to avoid leaking whether the email exists
        flash('If that email is registered, a reset link has been sent. Check your inbox.', 'info')
        return redirect(url_for('auth_login'))

    return render_template('forgot_password.html')


@app.route('/auth/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Let the user set a new password via a valid reset token."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    email = verify_reset_token(token)
    if email is None:
        flash('The reset link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('reset_password.html', token=token)

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', token=token)

        user = db.get_user_by_email(email)
        if user is None:
            flash('Account not found.', 'danger')
            return redirect(url_for('auth_login'))

        db.update_password(user.id, password)
        flash('Your password has been reset. Please log in.', 'success')
        return redirect(url_for('auth_login'))

    return render_template('reset_password.html', token=token)


@app.route('/guest')
def enter_guest():
    """Start a guest session without logging in."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    # Initialise empty guest data if not already present
    session.setdefault('guest_courses', {})
    session.setdefault('guest_deadlines', {})
    session.setdefault('guest_study_plans', [])
    flash('👋 You are browsing as a guest. Data will not be saved permanently. '
          '<a href="/auth/register" class="alert-link">Register</a> to keep your data.',
          'warning')
    return redirect(url_for('index'))


@app.route('/')
def index():
    """Dashboard - Display study plan overview."""
    courses, deadlines, study_plans = load_data()
    pending_notifications = []
    failed_notifications = []
    daily_summary_time = '08:00'

    if current_user.is_authenticated:
        daily_summary_time = get_daily_summary_time(current_user.id)
        pending_notifications = serialize_notifications(current_user.id, status='pending', limit=5)
        failed_notifications = serialize_notifications(current_user.id, status='failed', limit=5)
    
    # Add color coding and original index to study plans
    for i, plan in enumerate(study_plans):
        plan.color = get_deadline_color(plan.date, plan.completion_status)
        plan.original_index = i  # Store the original index in full list
    
    # Separate plans into upcoming and completed
    upcoming_plans = [p for p in study_plans if not p.completion_status]
    completed_plans = [p for p in study_plans if p.completion_status]
    
    return render_template(
        'index.html',
        upcoming_plans=upcoming_plans,
        completed_plans=completed_plans,
        courses=courses,
        deadlines=deadlines,
        pending_notifications=pending_notifications,
        failed_notifications=failed_notifications,
        daily_summary_time=daily_summary_time
    )


@app.route('/courses')
def view_courses():
    """Display all courses."""
    courses, _, _ = load_data()
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

        if current_user.is_authenticated:
            db.add_course(
                name=name,
                difficulty_level=difficulty,
                added_date=datetime.now().strftime("%Y-%m-%d"),
                user_id=current_user.id
            )
        else:
            _guest_warn()
            new_id = _next_guest_id(GUEST_COURSE_CTR)
            courses = _guest_courses()
            courses[str(new_id)] = {
                'course_id': new_id, 'name': name,
                'difficulty_level': difficulty,
                'added_date': datetime.now().strftime("%Y-%m-%d")
            }
            session['guest_courses'] = courses

        flash(f'Course "{name}" added successfully!', 'success')
        return redirect(url_for('view_courses'))
    
    return render_template('add_course.html')


@app.route('/deadlines')
def view_deadlines():
    """Display all deadlines."""
    courses, deadlines, _ = load_data()
    
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
    courses, _, _ = load_data()
    
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
        
        if current_user.is_authenticated:
            deadline = db.add_deadline(
                course_id=course_id,
                due_date=due_date_str,
                task_type=task_type,
                user_id=current_user.id
            )
            if deadline:
                flash(f'Deadline added for {courses[course_id].name}!', 'success')
            else:
                flash('Failed to add deadline.', 'danger')
        else:
            _guest_warn()
            new_id = _next_guest_id(GUEST_DEADLINE_CTR)
            deadlines = _guest_deadlines()
            deadlines[str(new_id)] = {
                'deadline_id': new_id, 'course_id': course_id,
                'due_date': due_date_str, 'task_type': task_type
            }
            session['guest_deadlines'] = deadlines
            flash(f'Deadline added for {courses[course_id].name}!', 'success')
        
        return redirect(url_for('view_deadlines'))
    
    return render_template('add_deadline.html', courses=courses)


@app.route('/study-plan/generate', methods=['POST'])
def generate_plan():
    """Generate a new study plan."""
    courses, deadlines, _ = load_data()
    
    if not deadlines:
        flash('Add deadlines before generating a study plan.', 'warning')
        return redirect(url_for('index'))

    study_plans = generate_study_plan_logic(courses, deadlines)
    save_study_plans(study_plans)

    if current_user.is_authenticated:
        notification_topic = db.get_scope_setting('notification_topic', user_id=current_user.id)
        if not notification_topic:
            flash('Email summaries are scheduled. Add an ntfy topic in Notification Settings if you also want open-source push notifications.', 'info')
    else:
        _guest_warn()
        flash('Guest mode can generate a study plan, but outbound daily reminders require a saved account.', 'info')

    flash(f'Study plan generated with {len(study_plans)} sessions!', 'success')
    return redirect(url_for('index'))


@app.route('/study-plan/complete/<int:session_index>', methods=['POST'])
def complete_session(session_index):
    """Mark a study session as complete."""
    if current_user.is_authenticated:
        success = db.update_study_session_status(session_index, True, user_id=current_user.id)
    else:
        plans = _guest_study_plans()
        if 0 <= session_index < len(plans):
            plans[session_index].completion_status = True
            _save_guest_study_plans(plans)
            success = True
            _guest_warn()
        else:
            success = False
    
    if success:
        flash('Session marked as complete!', 'success')
    else:
        flash('Invalid session.', 'danger')
    
    return redirect(url_for('index'))


@app.route('/study-plan/uncomplete/<int:session_index>', methods=['POST'])
def uncomplete_session(session_index):
    """Mark a study session as incomplete."""
    if current_user.is_authenticated:
        success = db.update_study_session_status(session_index, False, user_id=current_user.id)
    else:
        plans = _guest_study_plans()
        if 0 <= session_index < len(plans):
            plans[session_index].completion_status = False
            _save_guest_study_plans(plans)
            success = True
            _guest_warn()
        else:
            success = False
    
    if success:
        flash('Session marked as incomplete.', 'info')
    else:
        flash('Invalid session.', 'danger')
    
    return redirect(url_for('index'))


@app.route('/deadlines/edit/<int:deadline_id>', methods=['GET', 'POST'])
def edit_deadline(deadline_id):
    """Edit an existing deadline."""
    courses, deadlines, _ = load_data()
    
    if deadline_id not in deadlines:
        flash('Deadline not found.', 'danger')
        return redirect(url_for('view_deadlines'))
    
    if request.method == 'POST':
        due_date_str = request.form.get('due_date', '').strip()
        task_type = request.form.get('task_type', '').strip()
        
        try:
            datetime.strptime(due_date_str, "%Y-%m-%d")
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
            return redirect(url_for('edit_deadline', deadline_id=deadline_id))
        
        if not task_type:
            flash('Task type cannot be empty.', 'danger')
            return redirect(url_for('edit_deadline', deadline_id=deadline_id))

        if current_user.is_authenticated:
            success = db.update_deadline(deadline_id, due_date=due_date_str, task_type=task_type)
        else:
            _guest_warn()
            raw = _guest_deadlines()
            key = str(deadline_id)
            if key in raw:
                raw[key]['due_date'] = due_date_str
                raw[key]['task_type'] = task_type
                session['guest_deadlines'] = raw
                success = True
            else:
                success = False

        if success:
            flash('Deadline updated successfully!', 'success')
        else:
            flash('Failed to update deadline.', 'danger')
        
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
    courses, deadlines, _ = load_data()
    
    if deadline_id in deadlines:
        dl = deadlines[deadline_id]
        course_name = courses[dl.course_id].name if dl.course_id in courses else "Unknown"

        if current_user.is_authenticated:
            success = db.delete_deadline(deadline_id)
        else:
            _guest_warn()
            raw = _guest_deadlines()
            key = str(deadline_id)
            if key in raw:
                del raw[key]
                session['guest_deadlines'] = raw
                success = True
            else:
                success = False

        if success:
            flash(f'Deadline for {course_name} deleted.', 'info')
        else:
            flash('Failed to delete deadline.', 'danger')
    else:
        flash('Deadline not found.', 'danger')
    
    return redirect(url_for('view_deadlines'))


@app.route('/notifications')
def view_notifications():
    """Display scheduled daily summary notifications."""
    if not current_user.is_authenticated:
        _guest_warn()
        flash('Outbound notifications are available after you create an account and generate a study plan.', 'info')
        return render_template('notifications.html', notifications=[])

    notifications = serialize_notifications(current_user.id)
    smtp_failure = any(
        n['status'] == 'failed' and 'SMTP' in (n.get('error_message') or '')
        for n in notifications
    )
    return render_template('notifications.html', notifications=notifications, smtp_failure=smtp_failure)


@app.route('/settings/notifications', methods=['GET', 'POST'])
@login_required
def notification_settings():
    """Configure web notification settings for the logged-in user."""
    current_topic = db.get_scope_setting('notification_topic', user_id=current_user.id, default='') or ''
    current_time = get_daily_summary_time(current_user.id)

    if request.method == 'POST':
        notification_topic = request.form.get('notification_topic', '').strip()
        daily_summary_time = request.form.get('daily_summary_time', '').strip()
        normalized_time = normalize_summary_time(daily_summary_time)

        if normalized_time is None:
            flash('Daily summary time must use HH:MM.', 'danger')
            return redirect(url_for('notification_settings'))

        db.set_scope_setting('daily_summary_time', normalized_time, user_id=current_user.id)
        db.set_scope_setting('notification_topic', notification_topic, user_id=current_user.id)
        flash('Notification settings updated.', 'success')
        return redirect(url_for('notification_settings'))

    return render_template(
        'notification_settings.html',
        current_topic=current_topic,
        daily_summary_time=current_time,
        smtp_status=get_smtp_status()
    )


@app.route('/settings/notifications/test-email', methods=['POST'])
@login_required
def test_email():
    """Send a test email to the current user to verify SMTP configuration."""
    status = get_smtp_status()
    if not status['configured']:
        flash('SMTP is not fully configured. Check the status below and set the required environment variables.', 'danger')
        return redirect(url_for('notification_settings'))

    try:
        db._send_email(
            recipient=current_user.email,
            subject='Study Planner — Test Email ✅',
            body=(
                f'Hi {current_user.first_name or current_user.email},\n\n'
                'This is a test email from your Automated Study Planner.\n'
                'Your SMTP configuration is working correctly!'
            )
        )
        flash(f'Test email sent to {current_user.email}. Check your inbox!', 'success')
    except Exception as e:
        flash(f'Failed to send test email: {e}', 'danger')

    return redirect(url_for('notification_settings'))


@app.route('/analytics')
def analytics():
    """Progress tracking and analytics dashboard."""
    courses, deadlines, study_plans = load_data()

    today = datetime.now().date()

    # ── Core counts ──────────────────────────────────────────────────────────
    total_sessions = len(study_plans)
    completed_sessions = sum(1 for s in study_plans if s.completion_status)
    remaining_sessions = total_sessions - completed_sessions
    completion_rate = round(completed_sessions / total_sessions * 100) if total_sessions else 0

    # ── Study hours ──────────────────────────────────────────────────────────
    total_planned_hours = round(sum(s.duration for s in study_plans) / 60, 1)
    completed_hours = round(sum(s.duration for s in study_plans if s.completion_status) / 60, 1)

    # ── Study streak (consecutive days with ≥1 completed session) ────────────
    completed_dates = sorted(
        {datetime.strptime(s.date, "%Y-%m-%d").date()
         for s in study_plans if s.completion_status},
        reverse=True
    )
    streak = 0
    if completed_dates:
        check = today
        for d in completed_dates:
            if d == check or d == check - timedelta(days=1):
                streak += 1
                check = d
            elif d < check - timedelta(days=1):
                break

    # ── Per-subject stats (for bar chart) ────────────────────────────────────
    subject_total: dict = defaultdict(int)
    subject_done: dict = defaultdict(int)
    for s in study_plans:
        subject_total[s.subject] += 1
        if s.completion_status:
            subject_done[s.subject] += 1
    subjects = sorted(subject_total.keys())
    subject_totals_list = [subject_total[sub] for sub in subjects]
    subject_done_list = [subject_done[sub] for sub in subjects]

    # ── Weekly study hours for the last 8 weeks (for line chart) ─────────────
    week_labels = []
    week_planned_hours = []
    week_completed_hours = []
    for weeks_ago in range(7, -1, -1):
        week_start = today - timedelta(days=today.weekday() + weeks_ago * 7)
        week_end = week_start + timedelta(days=6)
        week_labels.append(week_start.strftime("%-m/%-d"))
        planned = sum(
            s.duration for s in study_plans
            if week_start <= datetime.strptime(s.date, "%Y-%m-%d").date() <= week_end
        )
        done = sum(
            s.duration for s in study_plans
            if s.completion_status
            and week_start <= datetime.strptime(s.date, "%Y-%m-%d").date() <= week_end
        )
        week_planned_hours.append(round(planned / 60, 1))
        week_completed_hours.append(round(done / 60, 1))

    # ── Upcoming deadlines (top 5 future) ────────────────────────────────────
    course_map = {cid: c.name for cid, c in courses.items()}
    upcoming_deadlines = []
    for did, d in deadlines.items():
        try:
            due = datetime.strptime(d.due_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        days_left = (due - today).days
        if days_left >= 0:
            upcoming_deadlines.append({
                'course': course_map.get(d.course_id, 'Unknown'),
                'task_type': d.task_type,
                'due_date': d.due_date,
                'days_left': days_left,
                'color': get_deadline_color(d.due_date, False),
            })
    upcoming_deadlines.sort(key=lambda x: x['days_left'])
    upcoming_deadlines = upcoming_deadlines[:5]

    return render_template(
        'analytics.html',
        # summary stats
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        remaining_sessions=remaining_sessions,
        completion_rate=completion_rate,
        total_planned_hours=total_planned_hours,
        completed_hours=completed_hours,
        streak=streak,
        # chart data (JSON-serialised for JS)
        subjects_json=json.dumps(subjects),
        subject_totals_json=json.dumps(subject_totals_list),
        subject_done_json=json.dumps(subject_done_list),
        week_labels_json=json.dumps(week_labels),
        week_planned_json=json.dumps(week_planned_hours),
        week_completed_json=json.dumps(week_completed_hours),
        doughnut_json=json.dumps([completed_sessions, remaining_sessions]),
        # upcoming deadlines table
        upcoming_deadlines=upcoming_deadlines,
    )


start_notification_scheduler()


if __name__ == '__main__':
    app.run(debug=True)
