import os
import requests
from datetime import datetime

DEBUG_LOG_FILE = "gpt_summary_debug.txt"

# 🔐 Umgebungsvariablen aus GitHub Actions oder lokalem Setup
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DB_JOURNAL = os.environ.get("DB_JOURNAL")

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
        "sorts": [{"property": "Date", "direction": "descending"}],
        "page_size": 1
    }
    res = requests.post(url, json=payload, headers=headers)
    res.raise_for_status()
    results = res.json().get("results", [])
    return results[0] if results else None

def extract_rollup_text(entry, property_name):
    if property_name not in entry["properties"]:
        print(f"⚠️ Feld nicht gefunden: '{property_name}'")
        return ""
    
    prop = entry["properties"][property_name]
    if prop.get("type") == "rollup":
        rollup = prop.get("rollup", {})
        if rollup.get("type") == "array":
            return ", ".join([
                v.get("title", [{}])[0].get("text", {}).get("content", "")
                for v in rollup.get("array", []) if v.get("title")
            ])
        elif rollup.get("type") == "number":
            return str(rollup.get("number", ""))
        elif rollup.get("type") == "rich_text":
            return " ".join([
                rt.get("text", {}).get("content", "")
                for rt in rollup.get("rich_text", [])
            ])
    elif prop.get("type") == "rich_text":
        return " ".join([
            rt.get("text", {}).get("content", "")
            for rt in prop.get("rich_text", [])
        ])
    elif prop.get("type") == "multi_select":
        return ", ".join([v.get("name", "") for v in prop.get("multi_select", [])])
    return ""

def main():
    entry = get_latest_journal_entry()
    if not entry:
        print("❌ Kein Journaleintrag gefunden.")
        log_debug("❌ Kein Journaleintrag gefunden.")
        return

    print("📋 Verfügbare Properties im letzten Journaleintrag:")
    for key, prop in entry["properties"].items():
        print(f"- {key}: {prop.get('type')}")

    print("\n---------------------------")
    date_str = entry["properties"].get("Date", {}).get("date", {}).get("start", "Kein Datum")
    print(f"📅 Journaleintrag für: {date_str}")
    print("---------------------------")

    # ⚠️ Wichtig: Korrekte API-Feldnamen laut Debug
    fields_to_check = [
        "Projects",
        "Areas/Resources",
        "kategorien tasks",
        "kategorien notes",
        "notes-tags",
        "notes-typ",
        "Projectdescription",
        "Areasdescription",
        "Done:"  # <- wichtig!
    ]

    for field in fields_to_check:
        value = extract_rollup_text(entry, field)
        print(f"{field}: {value}")

if __name__ == "__main__":
    main()
