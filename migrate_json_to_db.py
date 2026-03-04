"""
Migration script to convert JSON storage to SQLite database.
Reads existing JSON files and imports them into the new database structure.
"""

import os
import json
from datetime import datetime
from database import DatabaseManager
from models import Course, Deadline, StudySession

def backup_json_files():
    """Backup existing JSON files before migration."""
    json_files = ['courses.json', 'deadlines.json', 'study_plans.json', 'counters.json']
    
    for filename in json_files:
        filepath = os.path.join('data', filename)
        if os.path.exists(filepath):
            backup_path = filepath + '.bak'
            # Read and write to create backup
            with open(filepath, 'r') as f:
                content = f.read()
            with open(backup_path, 'w') as f:
                f.write(content)
            print(f"✅ Backed up {filename} to {filename}.bak")

def load_json_file(filename, default):
    """Load a JSON file or return default if it doesn't exist."""
    filepath = os.path.join('data', filename)
    if not os.path.exists(filepath):
        return default
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default

def migrate_courses(db_manager):
    """Migrate courses from JSON to database."""
    courses_data = load_json_file('courses.json', {})
    
    if not courses_data:
        print("ℹ️  No courses to migrate")
        return 0
    
    count = 0
    for course_id, course_dict in courses_data.items():
        db_manager.add_course(
            name=course_dict['name'],
            difficulty_level=course_dict['difficulty_level'],
            added_date=course_dict['added_date']
        )
        count += 1
    
    print(f"✅ Migrated {count} courses")
    return count

def migrate_deadlines(db_manager):
    """Migrate deadlines from JSON to database."""
    deadlines_data = load_json_file('deadlines.json', {})
    
    if not deadlines_data:
        print("ℹ️  No deadlines to migrate")
        return 0
    
    count = 0
    for deadline_id, deadline_dict in deadlines_data.items():
        result = db_manager.add_deadline(
            course_id=deadline_dict['course_id'],
            due_date=deadline_dict['due_date'],
            task_type=deadline_dict['task_type']
        )
        if result:
            count += 1
        else:
            print(f"⚠️  Warning: Could not migrate deadline {deadline_id} (course not found)")
    
    print(f"✅ Migrated {count} deadlines")
    return count

def migrate_study_sessions(db_manager):
    """Migrate study sessions from JSON to database."""
    study_plans_data = load_json_file('study_plans.json', [])
    
    if not study_plans_data:
        print("ℹ️  No study sessions to migrate")
        return 0
    
    count = 0
    for session_dict in study_plans_data:
        db_manager.add_study_session(
            date=session_dict['date'],
            subject=session_dict['subject'],
            task_type=session_dict['task_type'],
            duration=session_dict['duration'],
            difficulty=session_dict['difficulty'],
            completion_status=session_dict.get('completion_status', False)
        )
        count += 1
    
    print(f"✅ Migrated {count} study sessions")
    return count

def main():
    """Run the migration process."""
    print("=" * 60)
    print("JSON to SQLite Migration Tool")
    print("=" * 60)
    print()
    
    # Check if data directory exists
    if not os.path.exists('data'):
        print("❌ Error: 'data' directory not found!")
        print("   No JSON files to migrate.")
        return
    
    # Check if any JSON files exist
    json_files = ['courses.json', 'deadlines.json', 'study_plans.json']
    has_data = any(os.path.exists(os.path.join('data', f)) for f in json_files)
    
    if not has_data:
        print("ℹ️  No JSON files found in 'data' directory.")
        print("   Nothing to migrate. You can start using the new database system.")
        return
    
    # Check if database already exists
    db_path = 'data/study_planner.db'
    if os.path.exists(db_path):
        response = input(f"\n⚠️  Database already exists at {db_path}\n   Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            return
        os.remove(db_path)
        print("✅ Removed existing database")
    
    print("\n📦 Starting migration...\n")
    
    # Backup JSON files
    backup_json_files()
    print()
    
    # Initialize database manager
    db_manager = DatabaseManager()
    print("✅ Database initialized\n")
    
    # Migrate data
    courses_count = migrate_courses(db_manager)
    deadlines_count = migrate_deadlines(db_manager)
    sessions_count = migrate_study_sessions(db_manager)
    
    print()
    print("=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"  Courses migrated:        {courses_count}")
    print(f"  Deadlines migrated:      {deadlines_count}")
    print(f"  Study sessions migrated: {sessions_count}")
    print()
    print("✅ All data successfully migrated to SQLite database")
    print(f"   Database location: {db_path}")
    print()
    print("📝 Your original JSON files have been backed up with .bak extension")
    print("   You can safely delete them once you verify the migration.")
    print()

if __name__ == '__main__':
    main()
