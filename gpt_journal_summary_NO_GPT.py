import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from openai import OpenAI
import requests

# 🔐 ENV laden
if os.path.exists(".env"):
    load_dotenv()

# 🔐 Secrets laden
NOTION_TOKEN    = os.getenv("NOTION_TOKEN")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")  # <- Muss VOR client-Aufruf passieren!
DB_TASKS        = os.getenv("DB_TASKS")
DB_JOURNAL      = os.getenv("DB_JOURNAL")
DB_NOTIZEN      = os.getenv("DB_NOTIZEN")

# 🔑 GPT-Client initialisieren
client = OpenAI(api_key=OPENAI_API_KEY)

DEBUG_LOG_FILE = "gpt_summary_debug.txt"

def log_debug(text):
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {text}\n")

def get_latest_journal_entry():
    url = "https://api.notion.com/v1/databases/{}/query".format(DB_JOURNAL)
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
    prop = entry.get("properties", {}).get(property_name, {})
    if prop.get("type") == "rollup":
        rollup = prop.get("rollup", {})
        if rollup.get("type") == "array":
            return ", ".join([v.get("title", [{}])[0].get("text", {}).get("content", "") for v in rollup.get("array", []) if v.get("title")])
        elif rollup.get("type") == "number":
            return str(rollup.get("number", ""))
        elif rollup.get("type") == "rich_text":
            return " ".join([rt.get("text", {}).get("content", "") for rt in rollup.get("rich_text", [])])
    elif prop.get("type") == "rich_text":
        return " ".join([rt.get("text", {}).get("content", "") for rt in prop.get("rich_text", [])])
    return ""

def generate_prompt(entry, date_str):
    return f""" Zusammenfassung für den {date_str}:
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
    ✅ Erledigte Tasks: {extract_rollup_text(entry, "Done")}% erledigt von der Gesamtanzahl der relevanten für diesen Tag. (ggf. aus dem %-Wert ableiten)

    ➤ Gib eine klare Zusammenfassung mit folgenden Schwerpunkten:
    - Woran wurde inhaltlich gearbeitet?
    - Gab es erkennbare thematische Häufungen?
    - Welche Learnings, Trends oder Empfehlungen lassen sich aus der Aktivität ableiten?
    - Gliedere in kurze Absätze, kein Bullet-Point-Stil.
    - Keine Wiederholung einzelner Titel, nur thematische Auswertung.
    """

def main():
    entry = get_latest_journal_entry()
    if not entry:
        log_debug("⚠️ Kein Journaleintrag gefunden.")
        return

    date_str = entry["properties"].get("Date", {}).get("date", {}).get("start", "")
    if not date_str:
        log_debug("⚠️ Kein Datum im Journaleintrag gefunden.")
        return

    prompt = generate_prompt(entry, date_str)
    log_debug("📨 GPT Prompt:\n" + prompt)

    print("🔍 TESTMODE: Generierter Prompt aus Notion-Daten")
    print("--------------------------------------------------")
    print(prompt)
    print("--------------------------------------------------")

    print("📌 Projekte:", extract_rollup_text(entry, "Projects"))
    print("📌 Bereiche:", extract_rollup_text(entry, "Areas/Resources"))
    print("🔖 Kategorien Tasks:", extract_rollup_text(entry, "kategorien tasks"))
    print("🔖 Kategorien Notes:", extract_rollup_text(entry, "kategorien notes"))
    print("🏷 Tags Notes:", extract_rollup_text(entry, "notes-tags"))
    print("📂 Typen Notes:", extract_rollup_text(entry, "notes-typ"))
    print("🧾 Beschreibung Projekte:", extract_rollup_text(entry, "Projectdescription"))
    print("🧾 Beschreibung Areas:", extract_rollup_text(entry, "Areasdescription"))
    print("✅ Done (%):", extract_rollup_text(entry, "Done"))

if __name__ == "__main__":
    main()
