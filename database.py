"""
Database module for Automated Study Planner using SQLAlchemy ORM.
Supports both SQLite (development) and PostgreSQL (production/Heroku).
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from models import Course, Deadline, StudySession

Base = declarative_base()


class UserModel(Base, UserMixin):
    """SQLAlchemy model for users table."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(Date, nullable=False)

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
        
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self._migrate_add_user_columns()
        self.Session = sessionmaker(bind=self.engine)

    def _migrate_add_user_columns(self) -> None:
        """Add user_id columns to existing tables if they don't exist (SQLite migration)."""
        with self.engine.connect() as conn:
            for table, col_def in [
                ('courses', 'user_id INTEGER REFERENCES users(id)'),
                ('deadlines', 'user_id INTEGER REFERENCES users(id)'),
                ('study_sessions', 'user_id INTEGER REFERENCES users(id)'),
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
    
    def add_study_session(self, date: str, subject: str, task_type: str,
                         duration: int, difficulty: int, 
                         completion_status: bool = False) -> StudySession:
        """Add a new study session to the database."""
        session = self.get_session()
        try:
            session_model = StudySessionModel(
                date=datetime.strptime(date, "%Y-%m-%d").date(),
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
            query = session.query(StudySessionModel).order_by(StudySessionModel.date)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            sessions = query.all()
            return [s.to_dataclass() for s in sessions]
        finally:
            session.close()
    
    def update_study_session_status(self, session_index: int, completion_status: bool,
                                     user_id: Optional[int] = None) -> bool:
        """Update completion status of a study session by index (within user scope)."""
        session = self.get_session()
        try:
            query = session.query(StudySessionModel).order_by(StudySessionModel.date)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
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
        """Replace all study sessions (for user) with a new list."""
        session = self.get_session()
        try:
            # Delete existing sessions for this user (or all if no user)
            query = session.query(StudySessionModel)
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            query.delete()
            
            # Add new sessions
            for study_session in study_sessions:
                session_model = StudySessionModel(
                    date=datetime.strptime(study_session.date, "%Y-%m-%d").date(),
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
