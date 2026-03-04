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
from models import Course, Deadline, StudySession

Base = declarative_base()


class CourseModel(Base):
    """SQLAlchemy model for Course table."""
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    difficulty_level = Column(Integer, nullable=False)
    added_date = Column(Date, nullable=False)
    
    deadlines = relationship("DeadlineModel", back_populates="course", cascade="all, delete-orphan")
    
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
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        """Get a new database session."""
        return self.Session()
    
    # ==================== COURSE CRUD OPERATIONS ====================
    
    def add_course(self, name: str, difficulty_level: int, added_date: str) -> Course:
        """Add a new course to the database."""
        session = self.get_session()
        try:
            course_model = CourseModel(
                name=name,
                difficulty_level=difficulty_level,
                added_date=datetime.strptime(added_date, "%Y-%m-%d").date()
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
    
    def get_all_courses(self) -> Dict[int, Course]:
        """Get all courses as a dictionary keyed by course_id."""
        session = self.get_session()
        try:
            courses = session.query(CourseModel).all()
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
    
    def add_deadline(self, course_id: int, due_date: str, task_type: str) -> Optional[Deadline]:
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
                task_type=task_type
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
    
    def get_all_deadlines(self) -> Dict[int, Deadline]:
        """Get all deadlines as a dictionary keyed by deadline_id."""
        session = self.get_session()
        try:
            deadlines = session.query(DeadlineModel).all()
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
    
    def get_all_study_sessions(self) -> List[StudySession]:
        """Get all study sessions sorted by date."""
        session = self.get_session()
        try:
            sessions = session.query(StudySessionModel).order_by(StudySessionModel.date).all()
            return [s.to_dataclass() for s in sessions]
        finally:
            session.close()
    
    def update_study_session_status(self, session_index: int, completion_status: bool) -> bool:
        """Update completion status of a study session by index."""
        session = self.get_session()
        try:
            # Get all sessions sorted by date
            sessions = session.query(StudySessionModel).order_by(StudySessionModel.date).all()
            
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
    
    def save_study_sessions(self, study_sessions: List[StudySession]) -> None:
        """Replace all study sessions with a new list."""
        session = self.get_session()
        try:
            # Delete existing sessions
            session.query(StudySessionModel).delete()
            
            # Add new sessions
            for study_session in study_sessions:
                session_model = StudySessionModel(
                    date=datetime.strptime(study_session.date, "%Y-%m-%d").date(),
                    subject=study_session.subject,
                    task_type=study_session.task_type,
                    duration=study_session.duration,
                    difficulty=study_session.difficulty,
                    completion_status=study_session.completion_status
                )
                session.add(session_model)
            
            session.commit()
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
