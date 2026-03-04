"""
Automated Study Planner - CLI Prototype with Persistent Storage
Main application file for managing courses, deadlines, and generating study plans.
"""

from tabulate import tabulate
from datetime import datetime, timedelta
from database import DatabaseManager
from models import Course, Deadline, StudySession


class StudyPlanner:
    """CLI-based study planner with persistent database storage."""
    
    def __init__(self):
        self.db = DatabaseManager()
        
        # Load persisted data
        self.courses = self.db.get_all_courses()
        self.deadlines = self.db.get_all_deadlines()
        self.study_plans = self.db.get_all_study_sessions()
    
    def add_course(self, name, difficulty_level):
        """Add a new course. Difficulty 1-5."""
        if not 1 <= difficulty_level <= 5:
            print("❌ Difficulty level must be between 1 and 5.")
            return
        
        course = self.db.add_course(
            name=name,
            difficulty_level=difficulty_level,
            added_date=datetime.now().strftime("%Y-%m-%d")
        )
        self.courses = self.db.get_all_courses()
        print(f"✅ Course '{name}' added with ID {course.course_id} (Difficulty: {difficulty_level}/5)")
        return course.course_id
    
    def add_deadline(self, course_id, due_date_str, task_type):
        """Add a deadline for a course. Date format: YYYY-MM-DD."""
        if course_id not in self.courses:
            print(f"❌ Course ID {course_id} not found.")
            return
        
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD.")
            return
        
        if due_date < datetime.now():
            print("❌ Due date must be in the future.")
            return
        
        deadline = self.db.add_deadline(
            course_id=course_id,
            due_date=due_date_str,
            task_type=task_type
        )
        
        if deadline:
            self.deadlines = self.db.get_all_deadlines()
            print(f"✅ Deadline added: {self.courses[course_id].name} - {task_type} due {due_date_str}")
            return deadline.deadline_id
        else:
            print(f"❌ Failed to add deadline.")
            return None
    
    def generate_study_plan(self, start_date_str=None):
        """Generate a basic study plan based on courses and deadlines."""
        if not self.deadlines:
            print("❌ No deadlines added. Cannot generate study plan.")
            return
        
        if start_date_str is None:
            start_date = datetime.now().date()
        else:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD.")
                return
        
        self.study_plans = []
        
        # Sort deadlines by due date
        sorted_deadlines = sorted(
            self.deadlines.items(),
            key=lambda x: datetime.strptime(x[1].due_date, "%Y-%m-%d")
        )
        
        # Generate study sessions
        for deadline_id, deadline_info in sorted_deadlines:
            course_id = deadline_info.course_id
            course = self.courses[course_id]
            due_date = datetime.strptime(deadline_info.due_date, "%Y-%m-%d").date()
            
            # Calculate days until deadline
            days_until = (due_date - start_date).days
            if days_until < 0:
                continue  # Skip past deadlines
            
            # Calculate study duration based on difficulty (harder = longer sessions)
            difficulty = course.difficulty_level
            base_duration = 60  # minutes
            total_study_time = base_duration * difficulty  # Multiply by difficulty
            sessions_count = max(2, difficulty)  # At least 2 sessions per course
            duration_per_session = total_study_time // sessions_count
            
            # Spread sessions across available days
            session_dates = self._distribute_sessions(
                start_date, due_date, sessions_count
            )
            
            for session_date in session_dates:
                self.study_plans.append(StudySession(
                    date=session_date.strftime("%Y-%m-%d"),
                    subject=course.name,
                    task_type=deadline_info.task_type,
                    duration=duration_per_session,
                    difficulty=difficulty,
                    completion_status=False
                ))
        
        # Sort by date
        self.study_plans.sort(key=lambda x: x.date)
        self.db.save_study_sessions(self.study_plans)
        print(f"✅ Study plan generated with {len(self.study_plans)} sessions.")
    
    def _distribute_sessions(self, start_date, end_date, num_sessions):
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
        if sessions[-1] < end_date:
            sessions.append(end_date)
        
        return sessions
    
    def display_courses(self):
        """Display all added courses in a table format."""
        if not self.courses:
            print("📚 No courses added yet.")
            return
        
        table_data = [
            [cid, data.name, f"{data.difficulty_level}/5", data.added_date]
            for cid, data in self.courses.items()
        ]
        headers = ["Course ID", "Course Name", "Difficulty", "Added Date"]
        print("\n📚 Courses:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def display_deadlines(self):
        """Display all added deadlines in a table format."""
        if not self.deadlines:
            print("📅 No deadlines added yet.")
            return
        
        table_data = []
        for did, data in self.deadlines.items():
            course_name = self.courses[data.course_id].name
            table_data.append([
                did,
                course_name,
                data.task_type,
                data.due_date
            ])
        
        headers = ["Deadline ID", "Course", "Task Type", "Due Date"]
        print("\n📅 Deadlines:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def display_study_plan(self):
        """Display the generated study plan in a table format."""
        if not self.study_plans:
            print("📋 No study plan generated yet.")
            return
        
        table_data = [
            [
                plan.date,
                plan.subject,
                plan.task_type,
                f"{plan.duration} min",
                f"{plan.difficulty}/5",
                "✓" if plan.completion_status else "○"
            ]
            for plan in self.study_plans
        ]
        
        headers = ["Date", "Subject", "Task", "Duration", "Difficulty", "Status"]
        print("\n📋 Study Plan:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def mark_session_complete(self, session_index):
        """Mark a study session as complete."""
        if 0 <= session_index < len(self.study_plans):
            success = self.db.update_study_session_status(session_index, True)
            if success:
                self.study_plans = self.db.get_all_study_sessions()
                print(f"✅ Session marked as complete: {self.study_plans[session_index].subject}")
            else:
                print("❌ Failed to update session.")
        else:
            print("❌ Invalid session index.")
    
    def interactive_menu(self):
        """Run the interactive CLI menu."""
        print("\n" + "="*60)
        print("    🎓 AUTOMATED STUDY PLANNER - CLI PROTOTYPE 🎓")
        print("="*60)
        
        while True:
            print("\n--- Main Menu ---")
            print("1. Add Course")
            print("2. Add Deadline")
            print("3. View Courses")
            print("4. View Deadlines")
            print("5. Generate Study Plan")
            print("6. View Study Plan")
            print("7. Mark Session Complete")
            print("8. Exit")
            
            choice = input("\nEnter your choice (1-8): ").strip()
            
            if choice == "1":
                self._add_course_prompt()
            elif choice == "2":
                self._add_deadline_prompt()
            elif choice == "3":
                self.display_courses()
            elif choice == "4":
                self.display_deadlines()
            elif choice == "5":
                self._generate_plan_prompt()
            elif choice == "6":
                self.display_study_plan()
            elif choice == "7":
                self._mark_complete_prompt()
            elif choice == "8":
                print("\n👋 Thank you for using Automated Study Planner!")
                break
            else:
                print("❌ Invalid choice. Please try again.")
    
    def _add_course_prompt(self):
        """Prompt user to add a course."""
        name = input("Enter course name: ").strip()
        if not name:
            print("❌ Course name cannot be empty.")
            return
        
        try:
            difficulty = int(input("Enter difficulty level (1-5): ").strip())
            self.add_course(name, difficulty)
        except ValueError:
            print("❌ Difficulty must be an integer between 1 and 5.")
    
    def _add_deadline_prompt(self):
        """Prompt user to add a deadline."""
        self.display_courses()
        try:
            course_id = int(input("\nEnter course ID: ").strip())
            due_date = input("Enter due date (YYYY-MM-DD): ").strip()
            task_type = input("Enter task type (Exam/Assignment/Quiz/Project): ").strip()
            
            if not task_type:
                print("❌ Task type cannot be empty.")
                return
            
            self.add_deadline(course_id, due_date, task_type)
        except ValueError:
            print("❌ Invalid input.")
    
    def _generate_plan_prompt(self):
        """Prompt user to generate study plan."""
        start_date = input("Enter start date for plan (YYYY-MM-DD) [default: today]: ").strip()
        start_date = start_date if start_date else None
        self.generate_study_plan(start_date)
    
    def _mark_complete_prompt(self):
        """Prompt user to mark a session as complete."""
        self.display_study_plan()
        try:
            index = int(input("\nEnter session index (0-based): ").strip())
            self.mark_session_complete(index)
        except ValueError:
            print("❌ Invalid input.")


def main():
    """Entry point for the CLI application."""
    planner = StudyPlanner()
    planner.interactive_menu()


if __name__ == "__main__":
    main()
