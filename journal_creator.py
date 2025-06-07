import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import openai
import json

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_TASKS = os.getenv("DB_TASKS")
DB_NOTIZEN = os.getenv("DB_NOTIZEN")
DB_JOURNAL = os.getenv("DB_JOURNAL")
DB_PROJECTS = os.getenv("DB_PROJECTS")
DB_AREAS = os.getenv("DB_AREAS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

openai.api_key = OPENAI_API_KEY

def get_yesterday():
    return datetime.utcnow().date() - timedelta(days=1)

def query_database(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("results", [])

def filter_by_created_time(entries, target_date):
    return [
        entry for entry in entries
        if entry.get("created_time", "").startswith(target_date)
    ]

def extract_linked_ids(entries):
    return [entry["id"] for entry in entries]

def create_journal_entry(date_str, summary, task_ids, note_ids, project_ids, area_ids):
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": { "database_id": DB_JOURNAL },
        "properties": {
            "Name": { "title": [{ "text": { "content": f"Journal: {date_str}" } }] },
            "Date": { "date": { "start": date_str } },
            "Summary": { "rich_text": [{ "text": { "content": summary } }] },
            "Tasks": { "relation": [{"id": id} for id in task_ids] },
            "Notes": { "relation": [{"id": id} for id in note_ids] },
            "Projects": { "relation": [{"id": id} for id in project_ids] },
            "Areas/Resources": { "relation": [{"id": id} for id in area_ids] }
        }
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print("❌ Fehler beim Erstellen des Journals:", response.text)
    else:
        print("✅ Journaleintrag erfolgreich erstellt")

def main():
    yesterday = get_yesterday()
    yesterday_str = yesterday.isoformat()

    all_tasks = query_database(DB_TASKS)
    all_notes = query_database(DB_NOTIZEN)
    all_projects = query_database(DB_PROJECTS)
    all_areas = query_database(DB_AREAS)

    tasks = filter_by_created_time(all_tasks, yesterday_str)
    notes = filter_by_created_time(all_notes, yesterday_str)

    task_ids = extract_linked_ids(tasks)
    note_ids = extract_linked_ids(notes)
    project_ids = extract_linked_ids(all_projects)
    area_ids = extract_linked_ids(all_areas)

    summary = f"Zusammenfassung der Arbeit vom {yesterday.strftime('%d. %B %Y')}:"

    if not task_ids and not note_ids:
        summary += "\n- Es wurden keine Tasks oder Notizen erstellt."
    else:
        if task_ids:
            summary += f"\n- Insgesamt {len(task_ids)} neue Task(s)."
        if note_ids:
            summary += f"\n- Insgesamt {len(note_ids)} neue Notiz(en)."

    create_journal_entry(yesterday_str, summary, task_ids, note_ids, project_ids, area_ids)

if __name__ == "__main__":
    main()
