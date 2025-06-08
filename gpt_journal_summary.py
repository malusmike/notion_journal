import os
import requests
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv

# 🔐 ENV laden
if os.path.exists(".env"):
    load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_JOURNAL   = os.getenv("DB_JOURNAL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}
client = OpenAI(api_key=OPENAI_API_KEY)

DEBUG_LOG_FILE = "gpt_summary_debug.txt"

def log_debug(text):
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {text}\n")

def fetch_latest_journal_entry():
    url = f"https://api.notion.com/v1/databases/{DB_JOURNAL}/query"
    payload = {
        "page_size": 1,
        "sorts": [{"timestamp": "created_time", "direction": "descending"}]
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    data = response.json()
    if not data.get("results"):
        return None
    return data["results"][0]

def extract_text(prop, fallback="—"):
    try:
        return prop["rich_text"][0]["plain_text"]
    except Exception:
        return fallback

def extract_multi_select(prop):
    return [t["name"] for t in prop.get("multi_select", [])]

def extract_relation_titles(prop):
    return list({t["name"] for t in prop.get("rollup", {}).get("array", []) if "name" in t})

def generate_summary_prompt(date_str, values):
    return f"""
Zusammenfassung der Arbeitsaktivität am {date_str}:
nutze diese Informationen für den Eintrag: 
    📌 Projekte: {extract_rollup_text(entry, "Projects")}
    📌 Bereiche/Ressourcen: {extract_rollup_text(entry, "Areas/Resources")}

    🔖 Kategorien (Tasks): {extract_rollup_text(entry, "kategorien tasks")}
    🔖 Kategorien (Notes): {extract_rollup_text(entry, "kategorien notes")}
    🏷 Tags (Notes): {extract_rollup_text(entry, "notes-tags")}
    📂 Typen (Notes): {extract_rollup_text(entry, "notes-typ")}

    🧾 Beschreibung Projekte: {extract_rollup_text(entry, "Projectdescription")}
    🧾 Beschreibung Areas/Resources: {extract_rollup_text(entry, "Areasdescription")}
Der Eintrag im Feld Summary soll beinhalten: 
    ✅ Erledigte Tasks: {extract_rollup_text(entry, "Done")}% erledigt von der Gesamtanzahl dr relevanten für disen Tag. (ggf. aus dem %-Wert ableiten)

    ➤ Gib eine klare Zusammenfassung mit folgenden Schwerpunkten:
    - Woran wurde inhaltlich gearbeitet?
    - Gab es erkennbare thematische Häufungen?
    - Welche Learnings, Trends oder Empfehlungen lassen sich aus der Aktivität ableiten?
    - Gliedere in kurze Absätze, kein Bullet-Point-Stil.
    - Keine Wiederholung einzelner Titel, nur thematische Auswertung.
"""

def call_gpt(prompt):
    try:
        log_debug("📨 GPT Prompt: " + prompt)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=900,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log_debug("❌ GPT Fehler: " + str(e))
        return "GPT-Zusammenfassung konnte nicht erstellt werden."

def update_journal_summary(page_id, summary_text):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "Summary": {
                "rich_text": [{"text": {"content": summary_text}}]
            }
        }
    }
    res = requests.patch(url, headers=HEADERS, json=payload)
    log_debug("📤 Update Response: " + res.text)

def main():
    if os.path.exists(DEBUG_LOG_FILE):
        os.remove(DEBUG_LOG_FILE)

    entry = fetch_latest_journal_entry()
    if not entry:
        log_debug("❌ Kein Journaleintrag gefunden")
        return

    props = entry["properties"]
    date_str = props["Date"]["date"]["start"]
    log_debug(f"📅 Journal-Eintrag gefunden für: {date_str}")

    # Werte extrahieren
    values = {
        "tasks_created": props.get("Tasks", {}).get("rollup", {}).get("number", 0),
        "notes_created": props.get("Notes", {}).get("rollup", {}).get("number", 0),
        "tasks_edited": props.get("Tasks_edited", {}).get("rollup", {}).get("number", 0),
        "notes_edited": props.get("Notes_edited", {}).get("rollup", {}).get("number", 0),
        "inbox_tasks": props.get("Inbox", {}).get("rollup", {}).get("number", 0),
        "done_percent": int(props.get("Done", {}).get("number", 0)),
        "projects": extract_relation_titles(props.get("Projects", {})),
        "areas": extract_relation_titles(props.get("Areas/Resources", {})),
        "kategorien": extract_multi_select(props.get("kategorien tasks", {})) + extract_multi_select(props.get("kategorien notes", {})),
        "tags": extract_multi_select(props.get("notes-tags", {})),
        "typ": extract_multi_select(props.get("notes-typ", {}))
    }

    prompt = generate_summary_prompt(date_str, values)
    summary = call_gpt(prompt)
    update_journal_summary(entry["id"], summary)
    log_debug("✅ Journal aktualisiert.")

if __name__ == "__main__":
    main()
