import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests
import openai
import json

load_dotenv()

NOTION_TOKEN   = os.getenv("NOTION_TOKEN")
DB_TASKS       = os.getenv("DB_TASKS")
DB_JOURNAL     = os.getenv("DB_JOURNAL")
DB_NOTIZEN     = os.getenv("DB_NOTIZEN")
DB_PROJECTS    = os.getenv("DB_PROJECTS")
DB_AREAS       = os.getenv("DB_AREAS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

openai.api_key = OPENAI_API_KEY

def query_notion_database(db_id, filter_body=None):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    payload = {"page_size": 100}
    if filter_body:
        payload["filter"] = filter_body
    response = requests.post(url, headers=HEADERS, json=payload)
    return response.json()

def generate_gpt_summary(tasks_created, notes_created, all_tasks, all_projects, all_areas, date_str):
    try:
        num_tasks_created = len(tasks_created)
        num_notes_created = len(notes_created)

        edited_tasks = [
            task for task in all_tasks
            if "last_edited_time" in task and
               datetime.fromisoformat(task["last_edited_time"].replace("Z", "+00:00")).date() ==
               (datetime.utcnow() + timedelta(hours=4)).date() - timedelta(days=1)
        ]

        num_tasks_edited = len(edited_tasks)
        projects_seen = set()
        areas_seen = set()
        inbox_tasks = 0

        for task in edited_tasks:
            props = task.get("properties", {})
            proj = props.get("Projects", {}).get("relation", [])
            area = props.get("Areas/Resources", {}).get("relation", [])
            if not proj and not area:
                inbox_tasks += 1
            else:
                for p in proj:
                    projects_seen.add(p.get("id"))
                for a in area:
                    areas_seen.add(a.get("id"))

        prompt = f"""
Heute ist der {date_str}. Fasse meine Aktivitäten in einer produktiven, professionellen Sprache zusammen – kein Bullet-Style. Strukturiere die Zusammenfassung nach PARA-System, wenn möglich.

Berücksichtige:
- Ich habe {num_tasks_created} neue Tasks erstellt.
- Ich habe {num_notes_created} neue Notizen erstellt.
- Ich habe {num_tasks_edited} bestehende Tasks angesehen.
- Davon waren {inbox_tasks} Tasks ohne verlinktes Projekt oder Area/Resource (Inbox).
- Es waren Projekte (IDs): {list(projects_seen)}
- Es waren Areas/Resources (IDs): {list(areas_seen)}

Formuliere Learnings und Empfehlungen basierend auf dieser Aktivität.
"""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Du bist ein professioneller Produktivitätscoach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )

        return response.choices[0].message["content"].strip()

    except Exception as e:
        return f"GPT-Zusammenfassung konnte nicht erstellt werden. Fehler: {e}"

def main():
    dubai_tz = timezone(timedelta(hours=4))
    yesterday = datetime.now(dubai_tz).date() - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")

    created_filter = {
        "property": "Created time",
        "date": {
            "equals": yesterday.isoformat()
        }
    }

    tasks_created = query_notion_database(DB_TASKS, created_filter).get("results", [])
    notes_created = query_notion_database(DB_NOTIZEN, created_filter).get("results", [])
    all_tasks = query_notion_database(DB_TASKS).get("results", [])
    all_projects = query_notion_database(DB_PROJECTS).get("results", [])
    all_areas = query_notion_database(DB_AREAS).get("results", [])

    summary = generate_gpt_summary(tasks_created, notes_created, all_tasks, all_projects, all_areas, date_str)

    with open("journal_debug.txt", "w", encoding="utf-8") as f:
        f.write("DEBUG - Tasks created: " + str(len(tasks_created)) + "\n")
        f.write("DEBUG - Notes created: " + str(len(notes_created)) + "\n")
        f.write("DEBUG - Tasks total: " + str(len(all_tasks)) + "\n")
        f.write("DEBUG - Summary: " + summary + "\n")

    payload = {
        "parent": { "database_id": DB_JOURNAL },
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": f"Journal für {date_str}"
                        }
                    }
                ]
            },
            "Tasks": {
                "relation": [{"id": task["id"]} for task in tasks_created]
            },
            "Notes": {
                "relation": [{"id": note["id"]} for note in notes_created]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": summary
                            }
                        }
                    ]
                }
            }
        ]
    }

    response = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)
    if response.status_code != 200:
        print("❌ Fehler beim Erstellen des Journals (Statuscode", response.status_code, ")")
        print("📥 Response von Notion:")
        print(response.text)
    else:
        print("✅ Journal erfolgreich erstellt.")

if __name__ == "__main__":
    main()
