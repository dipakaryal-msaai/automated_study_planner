"""
Data models and storage management for Automated Study Planner.
Provides structured classes and JSON persistence layer.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional
from datetime import datetime
import json
import os


@dataclass
class Course:
    """Represents a course."""
    course_id: int
    name: str
    difficulty_level: int
    added_date: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> "Course":
        """Create Course from dictionary."""
        return Course(**data)


@dataclass
class Deadline:
    """Represents a deadline for a course."""
    deadline_id: int
    course_id: int
    due_date: str
    task_type: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> "Deadline":
        """Create Deadline from dictionary."""
        return Deadline(**data)


@dataclass
class StudySession:
    """Represents a study session in the plan."""
    date: str
    subject: str
    task_type: str
    duration: int
    difficulty: int
    completion_status: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> "StudySession":
        """Create StudySession from dictionary."""
        return StudySession(**data)


class StorageManager:
    """Handles JSON-based persistence for study planner data."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize storage manager with data directory."""
        self.data_dir = data_dir
        self._ensure_data_directory()
        self.courses_file = os.path.join(data_dir, "courses.json")
        self.deadlines_file = os.path.join(data_dir, "deadlines.json")
        self.study_plans_file = os.path.join(data_dir, "study_plans.json")
        self.counters_file = os.path.join(data_dir, "counters.json")
    
    def _ensure_data_directory(self) -> None:
        """Create data directory if it doesn't exist."""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def load_courses(self) -> Dict[int, Course]:
        """Load courses from JSON file."""
        if not os.path.exists(self.courses_file):
            return {}
        
        try:
            with open(self.courses_file, "r") as f:
                data = json.load(f)
            return {int(k): Course.from_dict(v) for k, v in data.items()}
        except (json.JSONDecodeError, ValueError):
            return {}
    
    def load_deadlines(self) -> Dict[int, Deadline]:
        """Load deadlines from JSON file."""
        if not os.path.exists(self.deadlines_file):
            return {}
        
        try:
            with open(self.deadlines_file, "r") as f:
                data = json.load(f)
            return {int(k): Deadline.from_dict(v) for k, v in data.items()}
        except (json.JSONDecodeError, ValueError):
            return {}
    
    def load_study_plans(self) -> List[StudySession]:
        """Load study plans from JSON file."""
        if not os.path.exists(self.study_plans_file):
            return []
        
        try:
            with open(self.study_plans_file, "r") as f:
                data = json.load(f)
            return [StudySession.from_dict(item) for item in data]
        except (json.JSONDecodeError, ValueError):
            return []
    
    def load_counters(self) -> Dict[str, int]:
        """Load ID counters from JSON file."""
        if not os.path.exists(self.counters_file):
            return {"course_counter": 0, "deadline_counter": 0}
        
        try:
            with open(self.counters_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return {"course_counter": 0, "deadline_counter": 0}
    
    def save_courses(self, courses: Dict[int, Course]) -> None:
        """Save courses to JSON file."""
        data = {str(k): v.to_dict() for k, v in courses.items()}
        self._write_json(self.courses_file, data)
    
    def save_deadlines(self, deadlines: Dict[int, Deadline]) -> None:
        """Save deadlines to JSON file."""
        data = {str(k): v.to_dict() for k, v in deadlines.items()}
        self._write_json(self.deadlines_file, data)
    
    def save_study_plans(self, study_plans: List[StudySession]) -> None:
        """Save study plans to JSON file."""
        data = [plan.to_dict() for plan in study_plans]
        self._write_json(self.study_plans_file, data)
    
    def save_counters(self, counters: Dict[str, int]) -> None:
        """Save ID counters to JSON file."""
        self._write_json(self.counters_file, counters)
    
    def _write_json(self, filepath: str, data: any) -> None:
        """Write data to JSON file with error handling."""
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"⚠️  Warning: Could not save data to {filepath}: {e}")
    
    def clear_all(self) -> None:
        """Clear all stored data (for testing/reset)."""
        for filepath in [self.courses_file, self.deadlines_file, 
                        self.study_plans_file, self.counters_file]:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except IOError:
                    pass
