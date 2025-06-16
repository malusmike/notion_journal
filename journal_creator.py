import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests

# Lokale .env laden
if os.path.exists(".env"):
    load_dotenv()

# 🔐 Umgebungsvariablen
NOTION_TOKEN   = os.getenv("NOTION_TOKEN")
DB_TASKS       = os.getenv("DB_TASKS")
DB_JOURNAL     = os.getenv("DB_JOURNAL")
DB_NOTIZEN     = os.getenv("DB_NOTIZEN")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# Debug-Log-Datei per ENV-Variable steuerbar, Default journal_debug.txt
DEBUG_LOG_FILE = os.getenv("DEBUG_LOG_FILE", "journal_debug.txt")

def log_debug(text):
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def compute_yesterday():
    now = datetime.now(timezone.utc) + timedelta(hours=4)
    return (now - timedelta(days=1)).strftime("%Y-%m-%d")

def fetch_notion_db(db_id):
    results = []
    has_more = True
    next_cursor = None
    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor
        res = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=HEADERS,
            json=payload
        )
        res_json = res.json()
        results.extend(res_json.get("results", []))
        has_more = res_json.get("has_more", False)
        next_cursor = res_json.get("next_cursor")
    return results

def get_title_from_item(item):
    try:
        return item["properties"]["Name"]["title"][0]["text"]["content"]
    except Exception:
        return "(kein Titel)"

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

def create_journal_entry(date_str, tasks, notes):
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": DB_JOURNAL},
        "properties": {
            "Name":   {"title": [{"text": {"content": f"Journal für {date_str}"}}]},
            "Date":   {"date": {"start": date_str}},
            "Tasks":  {"relation": [{"id": t["id"]} for t in tasks]},
            "Notes":  {"relation": [{"id": n["id"]} for n in notes]}
        }
    }
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

    date_str  = compute_yesterday()
    all_tasks = fetch_notion_db(DB_TASKS)
    all_notes = fetch_notion_db(DB_NOTIZEN)

    tasks = filter_by_created_time(all_tasks, date_str)
    notes = filter_by_created_time(all_notes, date_str)

    create_journal_entry(date_str, tasks, notes)

if __name__ == "__main__":
    main()
