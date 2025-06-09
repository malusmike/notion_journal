import os
from dotenv import load_dotenv
from datetime import datetime
import requests

# 🔐 ENV laden
if os.path.exists(".env"):
    load_dotenv()

# 🔐 Secrets laden
NOTION_TOKEN    = os.getenv("NOTION_TOKEN")
DB_TASKS        = os.getenv("DB_TASKS")
DB_JOURNAL      = os.getenv("DB_JOURNAL")
DB_NOTIZEN      = os.getenv("DB_NOTIZEN")

DEBUG_LOG_FILE = "gpt_summary_debug.txt"

def log_debug(text):
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {text}\n")

def get_latest_journal_entry():
    url = f"https://api.notion.com/v1/databases/{DB_JOURNAL}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    payload = {
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        "page_size": 1
    }
    res = requests.post(url, json=payload, headers=headers)
    res.raise_for_status()
    results = res.json().get("results", [])
    return results[0] if results else None

def extract_rollup_text(entry, property_name):
    prop = entry.get("properties", {}).get(property_name, {})
    prop_type = prop.get("type")

    if prop_type == "rich_text":
        return " ".join([rt.get("text", {}).get("content", "") for rt in prop.get("rich_text", [])])
    elif prop_type == "rollup":
        rollup = prop.get("rollup", {})
        if rollup.get("type") == "rich_text":
            return " ".join([rt.get("text", {}).get("content", "") for rt in rollup.get("rich_text", [])])
        elif rollup.get("type") == "number":
            return str(rollup.get("number", ""))
    elif prop_type == "formula":
        formula = prop.get("formula", {})
        return str(formula.get(formula.get("type"), ""))
    return ""

def main():
    entry = get_latest_journal_entry()
    if not entry:
        log_debug("⚠️ Kein Journaleintrag gefunden.")
        print("❌ Kein Journaleintrag gefunden.")
        return

    # Titel zur Kontrolle
    name = entry["properties"].get("Name", {}).get("title", [])
    title = name[0]["text"]["content"] if name else "[kein Titel]"

    date_str = entry["properties"].get("Date", {}).get("date", {}).get("start", "Kein Datum")

    print(f"\n📅 Geladener Eintrag: {title}")
    print(f"📆 Datum: {date_str}")
    print("\n🧾 Inhalte aus vorbereiteten Textfeldern (Notion):\n")

    fields = [
        "textTasks",
        "textNotes",
        "textProjects",
        "textAreas",
        "textKategorienTasks",
        "textKategorienNotes",
        "textTagsNotes",
        "textTypNotes",
        "textProjectDescription",
        "textAreasDescription"
    ]

    for field in fields:
        value = extract_rollup_text(entry, field)
        print(f"{field}: {value if value else '[leer]'}")

if __name__ == "__main__":
    main()
