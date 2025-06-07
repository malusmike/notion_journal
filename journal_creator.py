import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests
import openai

# 📦 Lokales .env nur bei Bedarf laden
if os.path.exists(".env"):
    load_dotenv()

# 🔐 Secrets / Umgebungsvariablen
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
DEBUG_LOG_FILE = "journal_debug.txt"

def log_debug(text):
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def compute_yesterday():
    now = datetime.now(timezone.utc) + timedelta(hours=4)  # Dubai-Zeit
    yesterday = now - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")

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

def filter_by_created_time(items, date_str):
    target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    next_day = target + timedelta(days=1)
    filtered = []

    log_debug(f"📋 Analysezeitraum (UTC): {target.isoformat()} → {next_day.isoformat()}")
    log_debug(f"📦 Objekte insgesamt geladen: {len(items)}")

    for item in items:
        name = item.get("properties", {}).get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "(kein Titel)")
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

def generate_gpt_summary(tasks, notes):
    prompt = f"""Erstelle eine strukturierte Zusammenfassung der folgenden Aufgaben und Notizen vom Vortag. 
Nutze prägnante Stichpunkte, gegliedert nach Kategorien. Achte auf Klarheit und Struktur. 
Wenn sinnvoll, leite Learnings oder Empfehlungen ab.

**Aufgaben:** {tasks}
**Notizen:** {notes}
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log_debug(f"❌ GPT Fehler: {str(e)}")
        return "GPT-Zusammenfassung konnte nicht erstellt werden."

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

    # 🔍 Logge API-Call
    log_debug("📤 Request Payload an Notion:")
    log_debug(str(payload))
    response = requests.post(url, headers=HEADERS, json=payload)
    log_debug("📥 Response von Notion:")
    log_debug(response.text)

    if response.status_code != 200:
        log_debug(f"❌ Fehler beim Erstellen des Journals (Statuscode {response.status_code})")
    else:
        log_debug("✅ Journal erfolgreich erstellt.")

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

    summary = generate_gpt_summary([t["id"] for t in tasks], [n["id"] for n in notes])

    create_journal_entry(yesterday_str, tasks, notes, projects, areas, summary)

if __name__ == "__main__":
    main()
