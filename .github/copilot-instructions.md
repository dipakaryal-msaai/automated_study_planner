# Copilot Instructions - Automated Study Planner

## Project Overview

A CLI-based study planner that helps students manage courses, deadlines, and generates personalized study schedules. The application uses JSON-based persistent storage to maintain state across sessions.

## Running the Application

```bash
# Setup (first time only)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run the application
python main.py
```

The application runs an interactive menu-driven CLI with 8 options for managing courses, deadlines, and study plans.

## Architecture

### Core Components

- **`main.py`**: CLI application with interactive menu system
  - `StudyPlanner` class - Main orchestrator that manages courses, deadlines, and study plans
  - Uses `StorageManager` from `models.py` for persistence
  - All data operations trigger automatic saves via `_save_data()`

- **`models.py`**: Data models and persistence layer
  - Three dataclasses: `Course`, `Deadline`, `StudySession`
  - `StorageManager` class - Handles JSON serialization/deserialization
  - Each dataclass has `to_dict()` and `from_dict()` methods for JSON conversion

- **`data/`**: Persistent JSON storage (auto-created)
  - `courses.json` - Dict[int, Course] keyed by course_id
  - `deadlines.json` - Dict[int, Deadline] keyed by deadline_id  
  - `study_plans.json` - List[StudySession] sorted chronologically
  - `counters.json` - Maintains auto-increment IDs for courses/deadlines

### Key Data Flow

1. **Application startup**: `StudyPlanner.__init__()` loads all data from JSON files via `StorageManager`
2. **User modifications**: Any add/update/generate operation calls `_save_data()` to persist changes
3. **ID management**: Counters are loaded at startup and incremented for new entities to ensure unique IDs across sessions

## Important Conventions

### Study Plan Generation Algorithm

Located in `StudyPlanner.generate_study_plan()`:
- **Duration calculation**: `base_duration (60 min) × difficulty_level`
- **Session count**: `max(2, difficulty_level)` - ensures minimum 2 sessions per course
- **Distribution**: Sessions are spread evenly across days using `_distribute_sessions()` which calculates interval as `total_days // num_sessions`
- **Sorting**: Deadlines are processed in chronological order; final study plan is sorted by date
- **Past deadlines**: Automatically skipped during generation

### Date Handling

- All dates use `YYYY-MM-DD` string format (not datetime objects in storage)
- Dates are validated to be in the future when adding deadlines
- Session distribution ensures the last session falls on or before the deadline date

### Dataclass Pattern

All model classes follow this structure:
```python
@dataclass
class Entity:
    field1: type
    field2: type
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> "Entity":
        return Entity(**data)
```

This pattern is used for all entities (Course, Deadline, StudySession).

### Storage Layer Conventions

- `StorageManager` stores dict keys as strings in JSON (converted to int when loading)
- All load methods return empty collections (not None) if files don't exist
- JSON errors are caught and return default empty collections
- Write failures print warnings but don't crash the application
- Data directory is created automatically on first `StorageManager` initialization

### Completion Tracking

- Study sessions use 0-based indexing when marking complete
- `completion_status` is a boolean stored in each `StudySession`
- Display uses ✓/○ symbols to indicate completion status

## Error Handling Patterns

- Input validation with user-friendly error messages (❌ prefix)
- Success messages use ✅ prefix
- Date parsing wrapped in try/except with format guidance
- ID validation checks against existing collections before operations
- Storage operations silently handle missing files (return defaults)

## Dependencies

- **tabulate 0.9.0**: Table formatting for course/deadline/study plan display (uses "grid" format)
- **dataclasses**: Core Python (3.7+) for structured data
- **datetime**: Core Python for date operations
- **json/os**: Core Python for storage

## Future Architecture Notes

The README mentions planned features (Chunk 3+):
- SQLite migration (will replace JSON storage in `StorageManager`)
- User authentication (new module)
- ML-based scheduling (enhanced `generate_study_plan()` algorithm)
- Web interface (Flask backend, separate from CLI)

When implementing these, maintain backward compatibility with existing JSON storage or provide migration utilities.
