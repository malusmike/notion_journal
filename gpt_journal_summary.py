import os
import requests
from datetime import datetime

DEBUG_LOG_FILE = "gpt_summary_debug.txt"

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
                v.get("plain_text")
                or v.get("name")
                or v.get("text", {}).get("content", "")
                or v.get("title", [{}])[0].get("text", {}).get("content", "")
                for v in rollup.get("array", [])
            ])
        elif rollup.get("type") == "number":
            return str(rollup.get("number", ""))
        elif rollup.get("type") == "rich_text":
            return " ".join([
                rt.get("text", {}).get("content", "") for rt in rollup.get("rich_text", [])
            ])
    elif prop.get("type") == "multi_select":
        return ", ".join([v.get("name", "") for v in prop.get("multi_select", [])])
    elif prop.get("type") == "rich_text":
        return " ".join([
            rt.get("text", {}).get("content", "") for rt in prop.get("rich_text", [])
        ])
    elif prop.get("type") == "relation":
        return ", ".join([r.get("id", "") for r in prop.get("relation", [])])
    return ""

def get_possible_property(entry, label_variants):
    for label in label_variants:
        if label in entry["properties"]:
            return label
    print(f"⚠️ Keins der Felder gefunden: {', '.join(label_variants)}")
    return None

def generate_prompt(entry, date_str):
    done_field = get_possible_property(entry, ["Done", "Done %", "Done:", "Erledigt", "Status %"])
    done_value = extract_rollup_text(entry, done_field) if done_field else ""

    return f"""Zusammenfassung für den {date_str}:
Nutze diese Informationen für den Eintrag:

📌 Projekte: {extract_rollup_text(entry, "Projects")}
📌 Bereiche/Ressourcen: {extract_rollup_text(entry, "Areas/Resources")}

🔖 Kategorien (Tasks): {extract_rollup_text(entry, "kategorien tasks")}
🔖 Kategorien (Notes): {extract_rollup_text(entry, "kategorien notes")}
🏷 Tags (Notes): {extract_rollup_text(entry, "notes-tags")}
📂 Typen (Notes): {extract_rollup_text(entry, "notes-typ")}

🧾 Beschreibung Projekte: {extract_rollup_text(entry, "Projectdescription")}
🧾 Beschreibung Areas/Resources: {extract_rollup_text(entry, "Areasdescription")}

✅ Erledigte Tasks: {done_value} % erledigt von der Gesamtanzahl der relevanten für diesen Tag.

➤ Gib eine klare Zusammenfassung mit folgenden Schwerpunkten:
- Woran wurde inhaltlich gearbeitet?
- Gab es erkennbare thematische Häufungen?
- Welche Learnings, Trends oder Empfehlungen lassen sich aus der Aktivität ableiten?
- Gliedere in kurze Absätze, kein Bullet-Point-Stil.
- Keine Wiederholung einzelner Titel, nur thematische Auswertung."""

def main():
    entry = get_latest_journal_entry()
    if not entry:
        print("❌ Kein Journaleintrag gefunden.")
        log_debug("❌ Kein Journaleintrag gefunden.")
        return

    date_str = entry["properties"].get("Date", {}).get("date", {}).get("start", "Kein Datum")

    print("\n✅ Generierter GPT-Eingabe-Prompt:\n")
    prompt = generate_prompt(entry, date_str)
    print(prompt)
    print("\n🔍 Fertig. Alle verwendeten Notion-Werte wurden ausgelesen.")

if __name__ == "__main__":
    main()
