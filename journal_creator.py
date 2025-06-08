import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests
from gpt_summary import generate_gpt_summary

# 🔐 .env laden
if os.path.exists(".env"):
    load_dotenv()

NOTION_TOKEN   = os.getenv("NOTION_TOKEN")
DB_TASKS       = os.getenv("DB_TASKS")
DB_JOURNAL     = os.getenv("DB_JOURNAL")
DB_NOTIZEN     = os.getenv("DB_NOTIZEN")
DB_PROJECTS    = os.getenv("DB_PROJECTS")
DB_AREAS       = os.getenv("DB_AREAS")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

DEBUG_LOG_FILE = "journal_debug.txt"

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

# 📍 Filter nach Erstellungsdatum
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

# 📍 Filter nach letztem Bearbeitungsdatum
def filter_by_last_edited_time(items, date_str):
    target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    next_day = target + timedelta(days=1)
    return [
        item for item in items
        if target <= datetime.fromisoformat(item.get("last_edited_time", "").replace("Z", "+00:00")) < next_day
    ]

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

    date_str = compute_yesterday()
    log_debug(f"📅 Verarbeitung für: {date_str}")

    all_tasks    = fetch_notion_db(DB_TASKS)
    all_notes    = fetch_notion_db(DB_NOTIZEN)
    all_projects = fetch_notion_db(DB_PROJECTS)
    all_areas    = fetch_notion_db(DB_AREAS)

    new_tasks    = filter_by_created_time(all_tasks, date_str)
    new_notes    = filter_by_created_time(all_notes, date_str)
    edited_tasks = filter_by_last_edited_time(all_tasks, date_str)
    edited_notes = filter_by_last_edited_time(all_notes, date_str)

    inbox_tasks = [
        t for t in all_tasks
        if not t["properties"].get("Due Date", {}).get("date") and
           not t["properties"].get("Projects", {}).get("relation") and
           not t["properties"].get("Areas/Resources", {}).get("relation")
    ]

    linked_projects = list(set(
        p["properties"]["Name"]["title"][0]["text"]["content"]
        for t in all_tasks
        for p in all_projects
        if p["id"] in [r["id"] for r in t["properties"].get("Projects", {}).get("relation", [])]
    ))

    linked_areas = list(set(
        a["properties"]["Name"]["title"][0]["text"]["content"]
        for t in all_tasks
        for a in all_areas
        if a["id"] in [r["id"] for r in t["properties"].get("Areas/Resources", {}).get("relation", [])]
    ))

    tags_and_categories = list(set(
        tag["name"]
        for t in all_tasks
        for tag in t["properties"].get("Tags", {}).get("multi_select", []) +
                    t["properties"].get("Kategorie", {}).get("multi_select", [])
    ))

    summary = generate_gpt_summary(
        date_str=date_str,
        new_tasks=new_tasks,
        new_notes=new_notes,
        edited_tasks=edited_tasks,
        edited_notes=edited_notes,
        inbox_tasks=inbox_tasks,
        linked_projects=linked_projects,
        linked_areas=linked_areas,
        tags_and_categories=tags_and_categories
    )

    create_journal_entry(date_str, new_tasks, new_notes, all_projects, all_areas, summary)

if __name__ == "__main__":
    main()
