import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

DEBUG_LOG = "journal_debug.txt"
open(DEBUG_LOG, "w").write(f"# Journal Debug vom {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

def log_debug(text):
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def get_date_strings():
    today = datetime.now()
    target = today - timedelta(days=1)
    date_str = target.strftime("%Y-%m-%d")
    readable = f"{target.day}. {target.strftime('%B %Y')}"
    return date_str, readable

def query_all_items(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    all_items = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        response = requests.post(url, headers=HEADERS, json=payload)
        data = response.json()
        all_items.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")

    return all_items

def filter_by_edited_time(items, date_str):
    target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    next_day = target + timedelta(days=1)
    filtered = []

    log_debug(f"📋 Alle geladenen Tasks (nach lokaler Filterung für {date_str}):")
    for item in items:
        name = item.get("properties", {}).get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "(kein Titel)")
        edited_raw = item.get("last_edited_time")
        if edited_raw:
            edited = datetime.fromisoformat(edited_raw.replace("Z", "+00:00"))
            if target <= edited < next_day:
                filtered.append(item)
                log_debug(f"  • {name} — zuletzt bearbeitet: {edited_raw}")
    log_debug(f"✅ Gefilterte Tasks: {len(filtered)}\n")
    return filtered

def filter_by_created_time(items, date_str):
    target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    next_day = target + timedelta(days=1)
    filtered = []

    for item in items:
        created_raw = item.get("created_time")
        if created_raw:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            if target <= created < next_day:
                filtered.append(item)

    return filtered

def extract_related_ids(tasks, key):
    ids = set()
    for task in tasks:
        rels = task.get("properties", {}).get(key, {}).get("relation", [])
        for rel in rels:
            ids.add(rel["id"])
    return list(ids)

def generate_summary(date_str, tasks, notes, projects, areas):
    if not os.getenv("OPENAI_API_KEY"):
        return f"Tageszusammenfassung für {date_str} – GPT deaktiviert."

    import openai
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    inbox_tasks = [t for t in tasks if not (
        t.get("properties", {}).get("Projects", {}).get("relation") or
        t.get("properties", {}).get("Areas/Resources", {}).get("relation") or
        t.get("properties", {}).get("Notizen", {}).get("relation")
    )]

    prompt = f"""
Du bist ein produktiver Assistent. Erstelle eine prägnante Zusammenfassung meiner Arbeit vom {date_str}. Analysiere:

- Wie viele Tasks ({len(tasks)}) wurden bearbeitet?
- Wie viele Notizen ({len(notes)}) wurden erstellt?
- Welche Projekte ({len(projects)}) oder Areas ({len(areas)}) waren aktiv (über Tasks verknüpft)?
- Gibt es Inbox-Tasks ohne Verknüpfung? ({len(inbox_tasks)})
- Gibt es einen Trend im Vergleich zum Vortag oder zur Vorwoche?

Fasse das Ganze in **4–6 klaren Bullet Points** zusammen.
Sprache: Deutsch. Stil: professionell & fokussiert.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Du bist ein präziser Analyse-Assistent."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Fehler bei GPT-Zusammenfassung: {e}]"

def create_journal_entry(date_str, readable_date, tasks, notes, projects, areas, summary):
    url = "https://api.notion.com/v1/pages"
    db_id = os.getenv("DB_JOURNAL")

    properties = {
        "Name": {"title": [{"text": {"content": f"Journal: {readable_date}"}}]},
        "Date": {"date": {"start": date_str}},
        "Tasks": {"relation": [{"id": t["id"]} for t in tasks]},
        "Notizen": {"relation": [{"id": n["id"]} for n in notes]},
        "Projects": {"relation": [{"id": p} for p in projects]},
        "Areas/Resources": {"relation": [{"id": a} for a in areas]},
        "Summary": {"rich_text": [{"text": {"content": summary}}]}
    }

    response = requests.post(url, headers=HEADERS, json={
        "parent": {"database_id": db_id},
        "properties": properties
    })

    if response.status_code == 200:
        print("✅ Journal-Eintrag erfolgreich erstellt.")
    else:
        print("❌ Fehler:", response.text)

def main():
    date_str, readable_date = get_date_strings()
    print(f"📅 Verarbeite Einträge vom {date_str}")
    log_debug(f"🕒 Analyse für den {date_str}\n")

    all_tasks = query_all_items(os.getenv("DB_TASKS"))
    tasks = filter_by_edited_time(all_tasks, date_str)

    all_notes = query_all_items(os.getenv("DB_NOTES"))
    notes = filter_by_created_time(all_notes, date_str)

    project_ids = extract_related_ids(tasks, "Projects")
    area_ids = extract_related_ids(tasks, "Areas/Resources")

    summary = generate_summary(date_str, tasks, notes, project_ids, area_ids)
    log_debug(f"\n🧠 GPT-Zusammenfassung:\n{summary}\n")

    create_journal_entry(date_str, readable_date, tasks, notes, project_ids, area_ids, summary)

if __name__ == "__main__":
    main()
