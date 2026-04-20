"""
Standalone worker for processing daily study-summary notifications.
"""

import argparse
import os
import time
from dotenv import load_dotenv
from database import DatabaseManager

load_dotenv()


def main():
    """Run the notification worker once or in a loop."""
    parser = argparse.ArgumentParser(description="Process study planner daily notifications.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process due notifications once and exit.",
    )
    args = parser.parse_args()

    db = DatabaseManager()

    if args.once:
        results = db.process_due_notifications()
        print(f"Sent: {results['sent']}, Failed: {results['failed']}")
        return

    poll_interval = int(os.getenv("NOTIFICATION_POLL_INTERVAL_SECONDS", "60"))
    print(f"Notification worker started. Polling every {poll_interval} seconds.")

    while True:
        results = db.process_due_notifications()
        if results["sent"] or results["failed"]:
            print(f"Sent: {results['sent']}, Failed: {results['failed']}")
        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
