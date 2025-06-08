
import os
from notion_client import Client
from datetime import datetime, timedelta
from utils import (
    get_database_items,
    filter_by_date,
    get_database_id,
    create_journal_entry
)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
JOURNAL_DB_ID = os.getenv("JOURNAL_DB_ID")
TASKS_DB_ID = os.getenv("TASKS_DB_ID")
NOTES_DB_ID = os.getenv("NOTES_DB_ID")

notion = Client(auth=NOTION_TOKEN)

def main():
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")

    all_tasks = get_database_items(notion, TASKS_DB_ID)
    all_notes = get_database_items(notion, NOTES_DB_ID)

    new_tasks = filter_by_date(all_tasks, "created_time", date_str)
    new_notes = filter_by_date(all_notes, "created_time", date_str)

    if not new_tasks and not new_notes:
        print(f"No tasks or notes created on {date_str}. Skipping journal entry.")
        return

    create_journal_entry(
        notion=notion,
        date_str=date_str,
        journal_db_id=JOURNAL_DB_ID,
        new_tasks=new_tasks,
        new_notes=new_notes
    )

if __name__ == "__main__":
    main()
