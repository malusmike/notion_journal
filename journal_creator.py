import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests
from openai import OpenAI

# .env laden (nur lokal erforderlich)
load_dotenv()

# Konfig
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

client = OpenAI(api_key=OPENAI_API_KEY)

def query_notion_database(db_id, filter_body=None):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    payload = {"page_size": 100}
    if filter_body:
        payload["filter"] = filter_body
    response = requests.post(url, headers=HEADERS, json=payload)
    return response.json()

def generate_gpt_summary(tasks_created, notes_created, all_tasks, date_str):
    try:
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        tasks_edited = [
            t for t in all_tasks
            if "last_edited_time" in t and
               datetime.fromisoformat(t["last_edited_time"].replace("Z", "+00:00")).date() == yesterday
        ]

        inbox_count = 0
        seen_projects = set()
        seen_areas = set()

        for t in tasks_edited:
            props = t.get("properties", {})
            proj = props.get("Projects", {}).get("relation", [])
            area = props.get("Areas/Resources", {}).get("relation", [])
            if not proj and not area:
                inbox_count += 1
            seen_projects.update(p.get("id") for p in proj)
            seen_areas.update(a.get("id") for a in area)

        prompt = f"""Heute ist der {date_str}. Erstelle eine produktive, professionelle Tageszusammenfassung im Sinne des PARA-Systems.

Folgende Aktivität liegt vor:

- Es wurden {len(tasks_created)} neue Tasks erstellt.
- Es wurden {len(notes_created)} neue Notizen erstellt.
- Es wurden {len(tasks_edited)} Tasks am Vortag bearbeitet.
- Davon waren {inbox_count} Inbox-Tasks (ohne Project/Area).
- Betroffene Projects (IDs): {list(seen_projects)}
- Betroffene Areas/Resources (IDs): {list(seen_areas)}

Analysiere den inhaltlichen Fokus, leite daraus mögliche Schwerpunkte und Learnings ab - keine Aufzählung einzelner Titel."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Du bist ein professioneller Produktivitätscoach."},
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.6,
            max_tokens=800
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"GPT-Zusammenfassung konnte nicht erstellt werden: {e}"

def main():
    dubai_tz = timezone(timedelta(hours=4))
    yesterday = datetime.now(dubai_tz).date() - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")

    filter_created = {
        "property": "Created time",
        "date": { "equals": yesterday.isoformat() }
    }

    tasks_created = query_notion_database(DB_TASKS, filter_created).get("results", [])
    notes_created = query_notion_database(DB_NOTIZEN, filter_created).get("results", [])
    all_tasks = query_notion_database(DB_TASKS).get("results", [])

    summary = generate_gpt_summary(tasks_created, notes_created, all_tasks, date_str)

    with open("journal_debug.txt", "w", encoding="utf-8") as f:
        f.write(f"DEBUG - Tasks created: {len(tasks_created)}\n")
        f.write(f"DEBUG - Notes created: {len(notes_created)}\n")
        f.write(f"DEBUG - Tasks total: {len(all_tasks)}\n")
        f.write(f"DEBUG - Summary: {summary}\n")

    payload = {
        "parent": { "database_id": DB_JOURNAL },
        "properties": {
            "Name": {
                "title": [{"text": {"content": f"Journal: {date_str}"}}]
            },
            "Date": {
                "date": { "start": yesterday.isoformat() }
            },
            "Tasks": {
                "relation": [{"id": t["id"]} for t in tasks_created]
            },
            "Notes": {
                "relation": [{"id": n["id"]} for n in notes_created]
            }
        },
        "children": [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": { "content": summary }
                }]
            }
        }]
    }

    res = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)
    if res.status_code != 200:
        print("❌ Fehler beim Erstellen:", res.status_code)
        print(res.text)
    else:
        print("✅ Journal erfolgreich erstellt.")

if __name__ == "__main__":
    main()
