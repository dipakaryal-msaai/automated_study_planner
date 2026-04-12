"""
Database module for Automated Study Planner using SQLAlchemy ORM.
Supports both SQLite (development) and PostgreSQL (production/Heroku).
"""

import os
import smtplib
from threading import RLock
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional
from email.message import EmailMessage
from urllib import request
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, Boolean, ForeignKey,
    CheckConstraint, DateTime
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from models import Course, Deadline, StudySession, Reminder

Base = declarative_base()
DEFAULT_STUDY_TIME = '18:00'


class UserModel(Base, UserMixin):
    """SQLAlchemy model for users table."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(Date, nullable=False)
    last_login = Column(DateTime, nullable=True)

    courses = relationship("CourseModel", back_populates="user", cascade="all, delete-orphan",
                           foreign_keys="CourseModel.user_id")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class CourseModel(Base):
    """SQLAlchemy model for Course table."""
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    difficulty_level = Column(Integer, nullable=False)
    added_date = Column(Date, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    deadlines = relationship("DeadlineModel", back_populates="course", cascade="all, delete-orphan")
    user = relationship("UserModel", back_populates="courses", foreign_keys=[user_id])
    
    __table_args__ = (
        CheckConstraint('difficulty_level >= 1 AND difficulty_level <= 5', name='check_difficulty'),
    )
    
    def to_dataclass(self) -> Course:
        """Convert SQLAlchemy model to dataclass."""
        return Course(
            course_id=self.id,
            name=self.name,
            difficulty_level=self.difficulty_level,
            added_date=self.added_date.strftime("%Y-%m-%d")
        )


class DeadlineModel(Base):
    """SQLAlchemy model for Deadline table."""
    __tablename__ = 'deadlines'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    due_date = Column(Date, nullable=False)
    task_type = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    course = relationship("CourseModel", back_populates="deadlines")
    
    def to_dataclass(self) -> Deadline:
        """Convert SQLAlchemy model to dataclass."""
        return Deadline(
            deadline_id=self.id,
            course_id=self.course_id,
            due_date=self.due_date.strftime("%Y-%m-%d"),
            task_type=self.task_type
        )


class StudySessionModel(Base):
    """SQLAlchemy model for StudySession table."""
    __tablename__ = 'study_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    start_time = Column(String(5), nullable=False, default=DEFAULT_STUDY_TIME)
    subject = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    difficulty = Column(Integer, nullable=False)
    completion_status = Column(Boolean, default=False, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    def to_dataclass(self) -> StudySession:
        """Convert SQLAlchemy model to dataclass."""
        return StudySession(
            date=self.date.strftime("%Y-%m-%d"),
            start_time=self.start_time,
            subject=self.subject,
            task_type=self.task_type,
            duration=self.duration,
            difficulty=self.difficulty,
            completion_status=self.completion_status
        )


class MetadataModel(Base):
    """SQLAlchemy model for Metadata table (stores counters, settings)."""
    __tablename__ = 'metadata'
    
    key = Column(String, primary_key=True)
    value = Column(String)


class ReminderModel(Base):
    """SQLAlchemy model for scheduled outbound daily summary reminders."""
    __tablename__ = 'reminders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    summary_date = Column(Date, nullable=False)
    session_count = Column(Integer, nullable=False)
    greeting_name = Column(String, nullable=False)
    message = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    scheduled_for = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default='pending')
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)

    def to_dataclass(self) -> Reminder:
        """Convert SQLAlchemy model to a reminder dataclass."""
        return Reminder(
            reminder_id=self.id,
            summary_date=self.summary_date.strftime("%Y-%m-%d"),
            session_count=self.session_count,
            greeting_name=self.greeting_name,
            message=self.message,
            channel=self.channel,
            recipient=self.recipient,
            scheduled_for=self.scheduled_for.strftime("%Y-%m-%d %H:%M:%S"),
            status=self.status,
            sent_at=self.sent_at.strftime("%Y-%m-%d %H:%M:%S") if self.sent_at else None,
            error_message=self.error_message
        )


class DatabaseManager:
    """Manages all database operations using SQLAlchemy."""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            database_url: Database connection string. If None, uses environment variable
                         DATABASE_URL or defaults to SQLite.
        """
        if database_url is None:
            database_url = os.getenv('DATABASE_URL')
            if database_url is None:
                # Use absolute path for SQLite to avoid path issues
                base_dir = os.path.dirname(os.path.abspath(__file__))
                db_dir = os.path.join(base_dir, 'data')
                db_path = os.path.join(db_dir, 'study_planner.db')
                database_url = f'sqlite:///{db_path}'
        
        # Create data directory if using SQLite
        if database_url.startswith('sqlite'):
            # Extract path from sqlite:///path/to/db.db
            db_path = database_url.replace('sqlite:///', '')
            db_dir = os.path.dirname(db_path)
            os.makedirs(db_dir, exist_ok=True)

        engine_kwargs = {}
        if database_url.startswith('sqlite'):
            engine_kwargs['connect_args'] = {'check_same_thread': False}

        self.engine = create_engine(database_url, **engine_kwargs)
        Base.metadata.create_all(self.engine)
        self._migrate_schema_updates()
        self.Session = sessionmaker(bind=self.engine)
        self._notification_lock = RLock()

    def _migrate_schema_updates(self) -> None:
        """Apply lightweight SQLite migrations for newly added columns."""
        with self.engine.connect() as conn:
            for table, col_def in [
                ('courses', 'user_id INTEGER REFERENCES users(id)'),
                ('deadlines', 'user_id INTEGER REFERENCES users(id)'),
                ('study_sessions', 'user_id INTEGER REFERENCES users(id)'),
                ('study_sessions', f"start_time VARCHAR(5) NOT NULL DEFAULT '{DEFAULT_STUDY_TIME}'"),
                ('users', 'last_login DATETIME'),
            ]:
                try:
                    conn.execute(
                        __import__('sqlalchemy').text(
                            f'ALTER TABLE {table} ADD COLUMN {col_def}'
                        )
                    )
                    conn.commit()
                except Exception:
                    pass  # Column already exists

            try:
                column_rows = conn.execute(
                    __import__('sqlalchemy').text("PRAGMA table_info(reminders)")
                ).fetchall()
                column_names = {row[1] for row in column_rows}
                if column_names and 'summary_date' not in column_names:
                    conn.execute(__import__('sqlalchemy').text('DROP TABLE reminders'))
                    conn.commit()
                    ReminderModel.__table__.create(bind=self.engine, checkfirst=True)
            except Exception:
                pass
    
    def get_session(self):
        """Get a new database session."""
        return self.Session()
    
    # ==================== COURSE CRUD OPERATIONS ====================
    
    def add_course(self, name: str, difficulty_level: int, added_date: str,
                   user_id: Optional[int] = None) -> Course:
        """Add a new course to the database."""
        session = self.get_session()
        try:
            course_model = CourseModel(
                name=name,
                difficulty_level=difficulty_level,
                added_date=datetime.strptime(added_date, "%Y-%m-%d").date(),
                user_id=user_id
            )
            session.add(course_model)
            session.commit()
            course = course_model.to_dataclass()
            return course
        finally:
            session.close()
    
    def get_course(self, course_id: int) -> Optional[Course]:
        """Get a course by ID."""
        session = self.get_session()
        try:
            course_model = session.query(CourseModel).filter_by(id=course_id).first()
            return course_model.to_dataclass() if course_model else None
        finally:
            session.close()
    
    def get_all_courses(self, user_id: Optional[int] = None) -> Dict[int, Course]:
        """Get courses filtered by user_id (or all if None)."""
        session = self.get_session()
        try:
            query = session.query(CourseModel)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            courses = query.all()
            return {course.id: course.to_dataclass() for course in courses}
        finally:
            session.close()
    
    def update_course(self, course_id: int, name: Optional[str] = None, 
                     difficulty_level: Optional[int] = None) -> bool:
        """Update a course."""
        session = self.get_session()
        try:
            course = session.query(CourseModel).filter_by(id=course_id).first()
            if not course:
                return False
            
            if name is not None:
                course.name = name
            if difficulty_level is not None:
                course.difficulty_level = difficulty_level
            
            session.commit()
            return True
        finally:
            session.close()
    
    def delete_course(self, course_id: int) -> bool:
        """Delete a course and its associated deadlines."""
        session = self.get_session()
        try:
            course = session.query(CourseModel).filter_by(id=course_id).first()
            if not course:
                return False
            
            session.delete(course)
            session.commit()
            return True
        finally:
            session.close()
    
    # ==================== DEADLINE CRUD OPERATIONS ====================
    
    def add_deadline(self, course_id: int, due_date: str, task_type: str,
                     user_id: Optional[int] = None) -> Optional[Deadline]:
        """Add a new deadline to the database."""
        session = self.get_session()
        try:
            # Verify course exists
            course = session.query(CourseModel).filter_by(id=course_id).first()
            if not course:
                return None
            
            deadline_model = DeadlineModel(
                course_id=course_id,
                due_date=datetime.strptime(due_date, "%Y-%m-%d").date(),
                task_type=task_type,
                user_id=user_id
            )
            session.add(deadline_model)
            session.commit()
            return deadline_model.to_dataclass()
        finally:
            session.close()
    
    def get_deadline(self, deadline_id: int) -> Optional[Deadline]:
        """Get a deadline by ID."""
        session = self.get_session()
        try:
            deadline_model = session.query(DeadlineModel).filter_by(id=deadline_id).first()
            return deadline_model.to_dataclass() if deadline_model else None
        finally:
            session.close()
    
    def get_all_deadlines(self, user_id: Optional[int] = None) -> Dict[int, Deadline]:
        """Get deadlines filtered by user_id (or all if None)."""
        session = self.get_session()
        try:
            query = session.query(DeadlineModel)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            deadlines = query.all()
            return {deadline.id: deadline.to_dataclass() for deadline in deadlines}
        finally:
            session.close()
    
    def update_deadline(self, deadline_id: int, due_date: Optional[str] = None,
                        task_type: Optional[str] = None) -> bool:
        """Update a deadline."""
        session = self.get_session()
        try:
            deadline = session.query(DeadlineModel).filter_by(id=deadline_id).first()
            if not deadline:
                return False
            
            if due_date is not None:
                deadline.due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            if task_type is not None:
                deadline.task_type = task_type
            session.commit()
            return True
        finally:
            session.close()
    
    def delete_deadline(self, deadline_id: int) -> bool:
        """Delete a deadline."""
        session = self.get_session()
        try:
            deadline = session.query(DeadlineModel).filter_by(id=deadline_id).first()
            if not deadline:
                return False

            session.delete(deadline)
            session.commit()
            return True
        finally:
            session.close()
    
    # ==================== STUDY SESSION CRUD OPERATIONS ====================
    
    def add_study_session(self, date: str, start_time: str, subject: str, task_type: str,
                         duration: int, difficulty: int,
                         completion_status: bool = False) -> StudySession:
        """Add a new study session to the database."""
        session = self.get_session()
        try:
            session_model = StudySessionModel(
                date=datetime.strptime(date, "%Y-%m-%d").date(),
                start_time=start_time,
                subject=subject,
                task_type=task_type,
                duration=duration,
                difficulty=difficulty,
                completion_status=completion_status
            )
            session.add(session_model)
            session.commit()
            return session_model.to_dataclass()
        finally:
            session.close()
    
    def get_all_study_sessions(self, user_id: Optional[int] = None) -> List[StudySession]:
        """Get study sessions sorted by date, optionally filtered by user_id."""
        session = self.get_session()
        try:
            query = session.query(StudySessionModel).order_by(
                StudySessionModel.date,
                StudySessionModel.start_time
            )
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            else:
                query = query.filter(StudySessionModel.user_id.is_(None))
            sessions = query.all()
            return [s.to_dataclass() for s in sessions]
        finally:
            session.close()
    
    def update_study_session_status(self, session_index: int, completion_status: bool,
                                     user_id: Optional[int] = None) -> bool:
        """Update completion status of a study session by index (within user scope)."""
        session = self.get_session()
        try:
            query = session.query(StudySessionModel).order_by(
                StudySessionModel.date,
                StudySessionModel.start_time
            )
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            else:
                query = query.filter(StudySessionModel.user_id.is_(None))
            sessions = query.all()
            
            if 0 <= session_index < len(sessions):
                sessions[session_index].completion_status = completion_status
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def clear_study_sessions(self) -> None:
        """Delete all study sessions."""
        session = self.get_session()
        try:
            session.query(StudySessionModel).delete()
            session.commit()
        finally:
            session.close()
    
    def save_study_sessions(self, study_sessions: List[StudySession],
                              user_id: Optional[int] = None) -> None:
        """Replace all *incomplete* study sessions (for user) with a new list.

        Completed sessions are never deleted — they form the permanent history
        that the analytics dashboard and streak counter rely on.
        """
        session = self.get_session()
        try:
            # Delete only incomplete sessions so completed history is preserved.
            query = session.query(StudySessionModel).filter_by(completion_status=False)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            else:
                query = query.filter(StudySessionModel.user_id.is_(None))

            if user_id is not None:
                session.query(ReminderModel).filter_by(
                    user_id=user_id,
                    status='pending'
                ).delete(synchronize_session=False)
            query.delete(synchronize_session=False)

            for study_session in study_sessions:
                session_model = StudySessionModel(
                    date=datetime.strptime(study_session.date, "%Y-%m-%d").date(),
                    start_time=study_session.start_time,
                    subject=study_session.subject,
                    task_type=study_session.task_type,
                    duration=study_session.duration,
                    difficulty=study_session.difficulty,
                    completion_status=study_session.completion_status,
                    user_id=user_id
                )
                session.add(session_model)

            session.commit()
        finally:
            session.close()
    
    # ==================== USER CRUD OPERATIONS ====================

    def create_user(self, email: str, first_name: str, last_name: str,
                    password: str) -> Optional['UserModel']:
        """Create a new user with hashed password. Returns None if email already exists."""
        session = self.get_session()
        try:
            if session.query(UserModel).filter_by(email=email.lower()).first():
                return None  # Email already taken
            user = UserModel(
                email=email.lower(),
                first_name=first_name,
                last_name=last_name,
                created_at=datetime.now().date()
            )
            user.set_password(password)
            session.add(user)
            session.commit()
            session.refresh(user)
            # Detach so the object can be used outside this session
            session.expunge(user)
            return user
        finally:
            session.close()

    def get_user_by_email(self, email: str) -> Optional['UserModel']:
        """Look up a user by email address."""
        session = self.get_session()
        try:
            user = session.query(UserModel).filter_by(email=email.lower()).first()
            if user:
                session.expunge(user)
            return user
        finally:
            session.close()

    def get_user_by_id(self, user_id: int) -> Optional['UserModel']:
        """Look up a user by primary key."""
        session = self.get_session()
        try:
            user = session.query(UserModel).filter_by(id=user_id).first()
            if user:
                session.expunge(user)
            return user
        finally:
            session.close()

    def update_password(self, user_id: int, new_password: str) -> bool:
        """Hash and save a new password for the given user. Returns True on success."""
        session = self.get_session()
        try:
            user = session.query(UserModel).filter_by(id=user_id).first()
            if user is None:
                return False
            user.set_password(new_password)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def update_last_login(self, user_id: int) -> None:
        """Stamp the current UTC time as last_login for the given user."""
        session = self.get_session()
        try:
            user = session.query(UserModel).filter_by(id=user_id).first()
            if user:
                user.last_login = datetime.utcnow()
                session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    # ==================== ADMIN OPERATIONS ====================

    def get_all_users_with_stats(self) -> list:
        """Return all users with per-user course/session/completion counts and last_login."""
        session = self.get_session()
        try:
            users = session.query(UserModel).order_by(UserModel.created_at.desc()).all()
            result = []
            for u in users:
                courses = session.query(CourseModel).filter_by(user_id=u.id).count()
                total_sessions = session.query(StudySessionModel).filter_by(user_id=u.id).count()
                completed = session.query(StudySessionModel).filter_by(
                    user_id=u.id, completion_status=True).count()
                result.append({
                    'id': u.id,
                    'full_name': u.full_name,
                    'email': u.email,
                    'created_at': u.created_at,
                    'last_login': u.last_login,
                    'courses': courses,
                    'total_sessions': total_sessions,
                    'completed_sessions': completed,
                })
            return result
        finally:
            session.close()

    def get_platform_stats(self) -> dict:
        """Return aggregate platform-wide stats."""
        session = self.get_session()
        try:
            total_users = session.query(UserModel).count()
            total_courses = session.query(CourseModel).count()
            total_sessions = session.query(StudySessionModel).count()
            completed_sessions = session.query(StudySessionModel).filter_by(
                completion_status=True).count()
            notifs_sent = session.query(ReminderModel).filter_by(status='sent').count()
            notifs_failed = session.query(ReminderModel).filter_by(status='failed').count()
            notifs_pending = session.query(ReminderModel).filter_by(status='pending').count()
            return {
                'total_users': total_users,
                'total_courses': total_courses,
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'notifs_sent': notifs_sent,
                'notifs_failed': notifs_failed,
                'notifs_pending': notifs_pending,
            }
        finally:
            session.close()

    def get_weekly_registrations(self, weeks: int = 8) -> list:
        """Return new-user counts per week for the last N weeks (oldest first)."""
        session = self.get_session()
        try:
            today = datetime.utcnow().date()
            result = []
            for i in range(weeks - 1, -1, -1):
                week_start = today - timedelta(days=today.weekday() + 7 * i)
                week_end = week_start + timedelta(days=6)
                count = session.query(UserModel).filter(
                    UserModel.created_at >= week_start,
                    UserModel.created_at <= week_end,
                ).count()
                result.append({'week': week_start.strftime('%b %d'), 'count': count})
            return result
        finally:
            session.close()

    # ==================== METADATA OPERATIONS ====================
    
    def get_metadata(self, key: str, default: str = None) -> Optional[str]:
        """Get a metadata value by key."""
        session = self.get_session()
        try:
            metadata = session.query(MetadataModel).filter_by(key=key).first()
            return metadata.value if metadata else default
        finally:
            session.close()
    
    def set_metadata(self, key: str, value: str) -> None:
        """Set a metadata value."""
        session = self.get_session()
        try:
            metadata = session.query(MetadataModel).filter_by(key=key).first()
            if metadata:
                metadata.value = value
            else:
                metadata = MetadataModel(key=key, value=value)
                session.add(metadata)
            session.commit()
        finally:
            session.close()

    @staticmethod
    def _scope_setting_key(setting_name: str, user_id: Optional[int] = None) -> str:
        """Build a metadata key for auth-scoped or legacy settings."""
        if user_id is None:
            return f'legacy:{setting_name}'
        return f'user:{user_id}:{setting_name}'

    def get_scope_setting(self, setting_name: str, user_id: Optional[int] = None,
                          default: Optional[str] = None) -> Optional[str]:
        """Get a scope-specific setting stored in metadata."""
        return self.get_metadata(self._scope_setting_key(setting_name, user_id), default)

    def set_scope_setting(self, setting_name: str, value: str,
                          user_id: Optional[int] = None) -> None:
        """Set a scope-specific setting stored in metadata."""
        self.set_metadata(self._scope_setting_key(setting_name, user_id), value)

    # ==================== NOTIFICATION OPERATIONS ====================

    @staticmethod
    def _scope_filter(column, user_id: Optional[int]):
        """Build a scope filter for legacy rows or authenticated user rows."""
        if user_id is None:
            return column.is_(None)
        return column == user_id

    @staticmethod
    def _get_metadata_value_for_session(session, key: str, default: Optional[str] = None) -> Optional[str]:
        """Read metadata within an existing SQLAlchemy session."""
        metadata = session.query(MetadataModel).filter_by(key=key).first()
        return metadata.value if metadata else default

    @staticmethod
    def _parse_summary_time(summary_time_str: str) -> time:
        """Parse the configured daily summary time."""
        return datetime.strptime(summary_time_str, "%H:%M").time()

    def _get_notification_targets(self, session, user: UserModel) -> Dict[str, Optional[str]]:
        """Resolve email and ntfy destinations for a user scope."""
        return {
            'email': user.email,
            'ntfy': self._get_metadata_value_for_session(
                session, f'user:{user.id}:notification_topic'
            ),
        }

    def _get_summary_schedule_time(self, session, user_id: int) -> time:
        """Resolve the daily reminder time for a user."""
        summary_time_str = self._get_metadata_value_for_session(
            session, f'user:{user_id}:daily_summary_time', '08:00'
        ) or '08:00'
        try:
            return self._parse_summary_time(summary_time_str)
        except ValueError:
            return time(hour=8, minute=0)

    @staticmethod
    def _build_notification_subject(summary_date, session_count: int) -> str:
        """Build an email subject for a daily study summary."""
        due_label = summary_date.strftime("%Y-%m-%d")
        session_label = 'session' if session_count == 1 else 'sessions'
        return f'Study planner summary for {due_label}: {session_count} {session_label}'

    @staticmethod
    def _build_notification_body(greeting_name: str, summary_date, session_count: int) -> str:
        """Build a daily summary body for email and ntfy."""
        session_label = 'study session' if session_count == 1 else 'study sessions'
        day_label = 'today' if summary_date == datetime.now().date() else summary_date.strftime("%Y-%m-%d")
        return f'Hey {greeting_name}, you have {session_count} {session_label} coming up {day_label}.'

    @staticmethod
    def _send_email(recipient: str, subject: str, body: str) -> None:
        """Send an email using SMTP environment configuration."""
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        smtp_from_email = os.getenv('SMTP_FROM_EMAIL') or smtp_username

        if not smtp_host or not smtp_from_email:
            raise RuntimeError('SMTP_HOST and SMTP_FROM_EMAIL (or SMTP_USERNAME) must be configured.')

        message = EmailMessage()
        message['Subject'] = subject
        message['From'] = smtp_from_email
        message['To'] = recipient
        message.set_content(body)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.starttls()
            if smtp_username and smtp_password:
                smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)

    @staticmethod
    def _send_ntfy(topic: str, subject: str, body: str) -> None:
        """Send a push notification via the open-source ntfy protocol."""
        server = os.getenv('NTFY_SERVER', 'https://ntfy.sh').rstrip('/')
        endpoint = f'{server}/{topic}'
        req = request.Request(endpoint, data=body.encode(), method='POST')
        req.add_header('Title', subject)
        req.add_header('Tags', 'calendar,books')
        with request.urlopen(req, timeout=30) as response:
            if response.status >= 400:
                raise RuntimeError(f'ntfy request failed with status {response.status}.')

    def sync_daily_summary_reminders(self, reference_datetime: Optional[datetime] = None) -> int:
        """Create or refresh a single daily summary reminder per user and channel."""
        current_datetime = reference_datetime or datetime.now()
        summary_date = current_datetime.date()
        created_or_updated = 0

        with self._notification_lock:
            session = self.get_session()
            try:
                users = (
                    session.query(UserModel)
                    .join(StudySessionModel, StudySessionModel.user_id == UserModel.id)
                    .filter(StudySessionModel.date == summary_date)
                    .distinct()
                    .all()
                )

                for user in users:
                    session_count = (
                        session.query(StudySessionModel)
                        .filter_by(user_id=user.id)
                        .filter(StudySessionModel.date == summary_date)
                        .count()
                    )
                    greeting_name = user.first_name or user.full_name.split()[0]
                    scheduled_for = datetime.combine(
                        summary_date,
                        self._get_summary_schedule_time(session, user.id)
                    )
                    message = self._build_notification_body(greeting_name, summary_date, session_count)
                    targets = self._get_notification_targets(session, user)

                    for channel, recipient in targets.items():
                        existing = (
                            session.query(ReminderModel)
                            .filter_by(user_id=user.id, summary_date=summary_date, channel=channel)
                            .first()
                        )

                        if not recipient or session_count == 0:
                            if existing and existing.status == 'pending':
                                session.delete(existing)
                                created_or_updated += 1
                            continue

                        if existing and existing.status == 'pending':
                            existing.recipient = recipient
                            existing.session_count = session_count
                            existing.greeting_name = greeting_name
                            existing.message = message
                            existing.scheduled_for = scheduled_for
                            created_or_updated += 1
                            continue

                        if existing:
                            continue

                        session.add(ReminderModel(
                            user_id=user.id,
                            summary_date=summary_date,
                            session_count=session_count,
                            greeting_name=greeting_name,
                            message=message,
                            channel=channel,
                            recipient=recipient,
                            scheduled_for=scheduled_for,
                            status='pending'
                        ))
                        created_or_updated += 1

                session.commit()
                return created_or_updated
            finally:
                session.close()

    def get_reminders(self, user_id: Optional[int] = None,
                      status: Optional[str] = None) -> List[Reminder]:
        """Get queued/sent/failed daily summary notifications for the requested scope."""
        session = self.get_session()
        try:
            query = (
                session.query(ReminderModel)
                .filter(self._scope_filter(ReminderModel.user_id, user_id))
            )
            if status:
                query = query.filter(ReminderModel.status == status)

            rows = query.order_by(
                ReminderModel.scheduled_for.asc(),
                ReminderModel.created_at.desc()
            ).all()

            return [reminder.to_dataclass() for reminder in rows]
        finally:
            session.close()

    def process_due_notifications(self, current_time: Optional[datetime] = None) -> Dict[str, int]:
        """Send any pending notifications that are due."""
        now = current_time or datetime.now()
        results = {'sent': 0, 'failed': 0}

        with self._notification_lock:
            self.sync_daily_summary_reminders(now)
            session = self.get_session()
            try:
                due_notifications = (
                    session.query(ReminderModel)
                    .filter(
                        ReminderModel.status == 'pending',
                        ReminderModel.scheduled_for <= now
                    )
                    .order_by(ReminderModel.scheduled_for.asc())
                    .all()
                )

                for reminder in due_notifications:
                    subject = self._build_notification_subject(
                        reminder.summary_date,
                        reminder.session_count
                    )
                    body = reminder.message

                    try:
                        if reminder.channel == 'email':
                            self._send_email(reminder.recipient, subject, body)
                        elif reminder.channel == 'ntfy':
                            self._send_ntfy(reminder.recipient, subject, body)
                        else:
                            raise RuntimeError(f'Unsupported notification channel: {reminder.channel}')

                        reminder.status = 'sent'
                        reminder.sent_at = now
                        reminder.error_message = None
                        results['sent'] += 1
                    except Exception as exc:
                        reminder.status = 'failed'
                        reminder.error_message = str(exc)
                        results['failed'] += 1

                session.commit()
                return results
            finally:
                session.close()
