import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests
from openai import OpenAI

# Lokales .env laden, falls vorhanden
if os.path.exists(".env"):
    load_dotenv()

# 🔐 Umgebungsvariablen
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

DEBUG_LOG_FILE = "journal_debug.txt"
client = OpenAI(api_key=OPENAI_API_KEY)

# 🪵 Logging
def log_debug(text):
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

# 🧠 Fallback für fehlende Titel
def get_title_from_item(item):
    try:
        return item["properties"]["Name"]["title"][0]["text"]["content"]
    except (KeyError, IndexError, TypeError):
        return "(kein Titel)"

# 📅 Datum für gestern (Dubai-Zeit)
def compute_yesterday():
    now = datetime.now(timezone.utc) + timedelta(hours=4)
    return (now - timedelta(days=1)).strftime("%Y-%m-%d")

# 🔁 Notion DB abfragen
def fetch_notion_db(db_id):
    results = []
    has_more = True
    next_cursor = None
    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor
        res = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=HEADERS, json=payload)
        res_json = res.json()
        results.extend(res_json.get("results", []))
        has_more = res_json.get("has_more", False)
        next_cursor = res_json.get("next_cursor")
    return results

# 🔍 Nur Items, die gestern erstellt wurden
def filter_by_created_time(items, date_str):
    target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    next_day = target + timedelta(days=1)
    filtered = []

    log_debug(f"📋 Analysezeitraum (UTC): {target.isoformat()} → {next_day.isoformat()}")
    log_debug(f"📦 Objekte insgesamt geladen: {len(items)}")

    for item in items:
        name = get_title_from_item(item)
        created_raw = item.get("created_time")
        if created_raw:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            log_debug(f"- {name} → created: {created.isoformat()}")
            if target <= created < next_day:
                log_debug("  ✅ Im Zeitfenster → übernommen")
                filtered.append(item)
            else:
                log_debug("  ⛔ Außerhalb des Zeitfensters → ignoriert")

    log_debug(f"✅ Gefilterte Objekte: {len(filtered)}\n")
    return filtered

# 🔍 Für GPT: Items, die gestern zuletzt bearbeitet wurden
def filter_by_last_edited_time(items, date_str):
    target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    next_day = target + timedelta(days=1)
    filtered = []

    log_debug(f"🕓 GPT-only Analyse: Last edited between {target.isoformat()} and {next_day.isoformat()}")
    for item in items:
        edited_raw = item.get("last_edited_time")
        if edited_raw:
            edited = datetime.fromisoformat(edited_raw.replace("Z", "+00:00"))
            if target <= edited < next_day:
                filtered.append(item)
    log_debug(f"🧠 GPT-only Items (last_edited_time): {len(filtered)}")
    return filtered

# 💬 GPT-Zusammenfassung
def generate_gpt_summary(tasks_created, notes_created, all_tasks, all_projects, all_areas, date_str):
    tasks_edited    = filter_by_last_edited_time(all_tasks, date_str)
    projects_edited = filter_by_last_edited_time(all_projects, date_str)
    areas_edited    = filter_by_last_edited_time(all_areas, date_str)

    prompt = f"""Erstelle eine strukturierte Zusammenfassung der Arbeitsaktivität vom {date_str}. 
Nutze klare, gegliederte Stichpunkte und leite sinnvolle Learnings oder Empfehlungen ab.

Berücksichtige folgende Quellen:

🔧 Neu erstellte Aufgaben:
{[get_title_from_item(t) for t in tasks_created]}

🗒️ Erstellte Notizen:
{[get_title_from_item(n) for n in notes_created]}

🛠️ Gestern bearbeitete Aufgaben:
{[get_title_from_item(t) for t in tasks_edited]}

📁 Gestern bearbeitete Projekte:
{[get_title_from_item(p) for p in projects_edited]}

🏷️ Gestern bearbeitete Areas/Resources:
{[get_title_from_item(a) for a in areas_edited]}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log_debug(f"❌ GPT Fehler: {str(e)}")
        return "GPT-Zusammenfassung konnte nicht erstellt werden."

# 📝 Journal-Eintrag erstellen
def create_journal_entry(date_str, tasks, notes, projects, areas, summary):
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": DB_JOURNAL},
        "properties": {
            "Name": {"title": [{"text": {"content": f"Journal: {date_str}"}}]},
            "Date": {"date": {"start": date_str}},
            "Tasks": {"relation": [{"id": t["id"]} for t in tasks]},
            "Notes": {"relation": [{"id": n["id"]} for n in notes]},
            "Projects": {"relation": [{"id": p["id"]} for p in projects]},
            "Areas/Resources": {"relation": [{"id": a["id"]} for a in areas]},
            "Summary": {"rich_text": [{"text": {"content": summary}}]}
        }
    }

    log_debug("📤 Request Payload an Notion:")
    log_debug(str(payload))
    response = requests.post(url, headers=HEADERS, json=payload)
    log_debug("📥 Response von Notion:")
    log_debug(response.text)

    if response.status_code != 200:
        log_debug(f"❌ Fehler beim Erstellen des Journals (Statuscode {response.status_code})")
    else:
        log_debug("✅ Journal erfolgreich erstellt.")

# 🚀 Main-Workflow
def main():
    if os.path.exists(DEBUG_LOG_FILE):
        os.remove(DEBUG_LOG_FILE)

    yesterday_str = compute_yesterday()
    log_debug(f"📅 Verarbeitung für: {yesterday_str}")

    all_tasks    = fetch_notion_db(DB_TASKS)
    all_notes    = fetch_notion_db(DB_NOTIZEN)
    all_projects = fetch_notion_db(DB_PROJECTS)
    all_areas    = fetch_notion_db(DB_AREAS)

    tasks    = filter_by_created_time(all_tasks, yesterday_str)
    notes    = filter_by_created_time(all_notes, yesterday_str)
    projects = filter_by_created_time(all_projects, yesterday_str)
    areas    = filter_by_created_time(all_areas, yesterday_str)

    summary = generate_gpt_summary(
        tasks_created=tasks,
        notes_created=notes,
        all_tasks=all_tasks,
        all_projects=all_projects,
        all_areas=all_areas,
        date_str=yesterday_str
    )

    create_journal_entry(yesterday_str, tasks, notes, projects, areas, summary)

if __name__ == "__main__":
    main()
